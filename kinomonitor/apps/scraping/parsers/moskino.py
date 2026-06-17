"""Парсер расписания городской сети «Москино» (mos-kino.ru/schedule/).

Одна страница содержит все ~20 кинотеатров сети с сеансами и ценами,
рендерится на сервере. Сеанс — ссылка вида
`javascript:ticketManager.richSession(ID)` с текстом «17:25 2D СУБ 420 P».
«СУБ» = показ на языке оригинала с субтитрами.

Привязка сеанса к фильму и кинотеатру — через ближайшие предшествующие
текстовые узлы (find_previous), без опоры на CSS-классы.
"""

import re
from datetime import datetime, time, timedelta
from decimal import Decimal

import httpx
from bs4 import BeautifulSoup
from django.conf import settings
from django.utils import timezone

from .base import BaseParser, SessionDTO

SCHEDULE_URL = "https://mos-kino.ru/schedule/?date={date}"

# Кинотеатры сети (название на сайте -> наш slug). Городская репертуарная
# сеть: ретроспективы, киноклубы, показы в оригинале — считаем нишевой.
KNOWN_CINEMAS = {
    "Ангара": "moskino-angara",
    "Вымпел": "moskino-vympel",
    "Чтиво": "moskino-chtivo",
    "Жуковский": "moskino-zhukovsky",
    "Искра": "moskino-iskra",
    "Кинопарк": "moskino-kinopark",
    "Космос": "moskino-kosmos",
    "Сокольники": "moskino-sokolniki",
    "Марс": "moskino-mars",
    "Молодёжный": "moskino-molodezhny",
    "Нева": "moskino-neva",
    "Рассвет": "moskino-rassvet",
    "Салют": "moskino-salut",
    "Сатурн": "moskino-saturn",
    "Спутник": "moskino-sputnik",
    "Тула": "moskino-tula",
    "Факел": "moskino-fakel",
    "Эльбрус": "moskino-elbrus",
    "Юность": "moskino-yunost",
    "Музеон": "moskino-muzeon",
    "Берёзка": "moskino-berezka",
}

SESSION_HREF = re.compile(r"richSession")
SESSION_TEXT = re.compile(
    r"^(?P<h>\d{1,2}):(?P<m>\d{2})\s+(?P<fmt>2D|3D|IMAX)?\s*(?P<sub>СУБ)?\s*"
    r"(?P<price>\d[\d\s]*)\s*[PР]$"
)
AGE_RE = re.compile(r"\d+\+\s*$")
MOVIE_LINE = re.compile(r"^(?P<head>.+?)\s*/\s*[^/]*мин[^/]*/")
TRAILING_YEAR = re.compile(r"\s(19\d{2}|20\d{2})$")


class MoskinoParser(BaseParser):
    source_slug = "moskino"
    source_name = "Москино"

    def fetch_sessions(self) -> list[SessionDTO]:
        result = []
        days = getattr(settings, "SCRAPE_DAYS_AHEAD", 3)
        with httpx.Client(
            headers={"User-Agent": settings.SCRAPER_USER_AGENT},
            timeout=15,
            follow_redirects=True,
        ) as client:
            for offset in range(1, days + 1):
                day = timezone.localdate() + timedelta(days=offset)
                resp = client.get(SCHEDULE_URL.format(date=day.isoformat()))
                if resp.status_code != 200:
                    continue
                result += self.parse_schedule(resp.text, day)
        return result

    # --- разбор (чистая функция, тестируется на фикстуре) ---

    def _cinema_map(self) -> dict[str, str]:
        """Встроенный список + кинотеатры сети из БД (добавленные через админку)."""
        mapping = dict(KNOWN_CINEMAS)
        try:
            from apps.catalog.models import Cinema

            for c in Cinema.objects.filter(network="Москино"):
                mapping.setdefault(c.name.replace(" (Москино)", ""), c.slug)
        except Exception:
            pass  # БД недоступна (юнит-тесты разбора) — хватит встроенного списка
        return mapping

    def parse_schedule(self, html: str, day) -> list[SessionDTO]:
        soup = BeautifulSoup(html, "lxml")
        known = self._cinema_map()
        result = []
        for a in soup.find_all("a", href=SESSION_HREF):
            m = SESSION_TEXT.match(a.get_text(" ", strip=True))
            if not m:
                continue
            movie = self._movie_for(a)
            cinema_name = self._cinema_for(a, known)
            if movie is None or cinema_name is None:
                continue
            title, year = movie
            starts = timezone.make_aware(
                datetime.combine(day, time(int(m["h"]), int(m["m"])))
            )
            price = Decimal(m["price"].replace(" ", ""))
            result.append(
                SessionDTO(
                    cinema_slug=known[cinema_name],
                    cinema_name=f"{cinema_name} (Москино)",
                    cinema_network="Москино",
                    cinema_is_niche=True,
                    movie_title=title,
                    movie_year=year,
                    starts_at=starts,
                    price_min=price,
                    price_max=price,
                    format=m["fmt"] or "2D",
                    original_language=bool(m["sub"]),
                )
            )
        return result

    def _movie_for(self, session_link) -> tuple[str, int | None] | None:
        """Ближайшая предшествующая строка вида «Название ГГГГ / 120 мин / … / 18+»."""
        node = session_link.find_previous(string=AGE_RE)
        for _ in range(3):
            if node is None:
                return None
            line = node.strip()
            m = MOVIE_LINE.match(line)
            if not m and node.parent is not None:
                # строка фильма может быть разбита на несколько узлов
                line = node.parent.get_text(" ", strip=True)
                m = MOVIE_LINE.match(line)
            if m:
                head = m["head"].strip().strip("«»")
                ym = TRAILING_YEAR.search(head)
                year = int(ym.group(1)) if ym else None
                title = TRAILING_YEAR.sub("", head).strip().strip("«»")
                return title, year
            node = node.find_previous(string=AGE_RE)
        return None

    def _cinema_for(self, session_link, known: dict[str, str]) -> str | None:
        node = session_link.find_previous(
            string=lambda t: t is not None and t.strip() in known
        )
        return node.strip() if node else None
