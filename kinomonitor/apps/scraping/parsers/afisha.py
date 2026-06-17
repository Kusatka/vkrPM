"""Парсер страниц кинотеатров на Афише.ру: расписание + цены «от N ₽».

Один класс обслуживает все кинотеатры с галочкой «Мониторим» в БД — так мы
закрываем и нишевый «Иллюзион» (билеты продаются только через Афишу),
и сетевой «КАРО 11 Октябрь». Страница «кинотеатр + дата» рендерится на
сервере. Пометка SUB у формата = показ на языке оригинала с субтитрами.

Разбор не привязан к CSS-классам: ищем карточку фильма от ссылки на него
и идём по текстовым токенам (формат -> цена -> время). Это переживает
смену вёрстки лучше, чем селекторы. Проверка на живом сайте: см. tests.
"""

import re
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal

import httpx
from bs4 import BeautifulSoup
from django.conf import settings
from django.utils import timezone

from .base import BaseParser, SessionDTO


@dataclass(frozen=True)
class AfishaCinema:
    slug: str  # наш внутренний код
    afisha_slug: str  # слаг с id на Афише, напр. "illyuzion-2692"
    name: str
    network: str = ""
    is_niche: bool = False


DEFAULT_CINEMAS = [
    AfishaCinema("illusion", "illyuzion-2692", "Иллюзион", "Госфильмофонд", True),
    AfishaCinema("karo-oktyabr", "karo-11-oktyabr-3103", "КАРО 11 Октябрь", "Каро", False),
]


def monitored_cinemas() -> list[AfishaCinema]:
    """Кинотеатры для опроса: из БД (галочка «Мониторим» в админке).

    Новые площадки попадают в БД задачей discover_cinemas. Если БД недоступна
    (юнит-тесты разбора, свежая установка до миграций) — встроенный список.
    """
    try:
        from apps.catalog.models import Cinema

        rows = Cinema.objects.filter(is_monitored=True).exclude(afisha_slug="")
        cinemas = [
            AfishaCinema(c.slug, c.afisha_slug, c.name, c.network, c.is_niche)
            for c in rows
        ]
    except Exception:
        return list(DEFAULT_CINEMAS)
    return cinemas or list(DEFAULT_CINEMAS)

DAY_URL = "https://www.afisha.ru/msk/cinema/{afisha_slug}/movie/{date}"

MOVIE_HREF = re.compile(r"/movie/[^/]+/\d{2}-\d{2}-\d{4}/?$")
TIME_RE = re.compile(r"^\d{1,2}:\d{2}$")
HAS_TIME_RE = re.compile(r"\b\d{1,2}:\d{2}\b")
PRICE_RE = re.compile(r"от\s*(\d[\d\s]*)\s*₽")
FORMAT_RE = re.compile(r"^(2D|3D|IMAX)\b(.*)$")
YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")


class AfishaParser(BaseParser):
    source_slug = "afisha"
    source_name = "Афиша.ру"

    def fetch_sessions(self) -> list[SessionDTO]:
        result = []
        days = getattr(settings, "SCRAPE_DAYS_AHEAD", 3)
        with httpx.Client(
            headers={"User-Agent": settings.SCRAPER_USER_AGENT},
            timeout=15,
            follow_redirects=True,
        ) as client:
            for cinema in monitored_cinemas():
                for offset in range(1, days + 1):
                    day = timezone.localdate() + timedelta(days=offset)
                    url = DAY_URL.format(
                        afisha_slug=cinema.afisha_slug, date=day.strftime("%d-%m-%Y")
                    )
                    resp = client.get(url)
                    if resp.status_code != 200:
                        continue
                    result += self.parse_day(resp.text, cinema, day)
        return result

    # --- разбор (чистые функции, тестируются на фикстурах) ---

    def parse_day(self, html: str, cinema: AfishaCinema, day) -> list[SessionDTO]:
        soup = BeautifulSoup(html, "lxml")
        seen, result = set(), []
        for link in soup.find_all("a", href=MOVIE_HREF):
            title = link.get_text(" ", strip=True)
            if not title or title in seen:
                continue
            seen.add(title)
            block = self._movie_block(link)
            if block is not None:
                result += self._parse_block(block, title, cinema, day)
        return result

    def _movie_block(self, link):
        """Подняться от ссылки на фильм до карточки с сеансами."""
        node, prev = link, None
        for _ in range(8):
            prev, node = node, node.parent
            if node is None:
                return None
            titles = {
                a.get_text(" ", strip=True)
                for a in node.find_all("a", href=MOVIE_HREF)
                if a.get_text(strip=True)
            }
            if len(titles) > 1:
                # поднялись до общего списка фильмов — карточкой был prev
                text = prev.get_text(" ", strip=True)
                return prev if HAS_TIME_RE.search(text) else None
            text = node.get_text(" ", strip=True)
            if HAS_TIME_RE.search(text) and (
                PRICE_RE.search(text) or "Нет билетов" in text
            ):
                return node
        return None

    def _parse_block(self, block, title, cinema: AfishaCinema, day) -> list[SessionDTO]:
        tokens = [t.strip() for t in block.stripped_strings if t.strip()]
        year = None
        for t in tokens[:8]:  # «2026, Биография» идёт сразу после названия
            m = YEAR_RE.search(t)
            if m and t != title:
                year = int(m.group(1))
                break

        sessions: list[SessionDTO] = []
        fmt, original, price = "2D", False, None
        for t in tokens:
            fm = FORMAT_RE.match(t)
            if fm:
                fmt = fm.group(1)
                original = "SUB" in fm.group(2).upper()
                price = None
                continue
            if t.upper() in ("SUB", "СУБ"):
                original = True
                continue
            pm = PRICE_RE.search(t)
            if pm:
                price = Decimal(pm.group(1).replace(" ", ""))
                continue
            if t == "Нет билетов":
                price = None
                continue
            if TIME_RE.match(t):
                h, minute = map(int, t.split(":"))
                sessions.append(
                    SessionDTO(
                        cinema_slug=cinema.slug,
                        cinema_name=cinema.name,
                        cinema_network=cinema.network,
                        cinema_is_niche=cinema.is_niche,
                        movie_title=title,
                        movie_year=year,
                        starts_at=timezone.make_aware(
                            datetime.combine(day, time(h, minute))
                        ),
                        price_min=price,
                        format=fmt,
                        original_language=original,
                    )
                )
                price = None  # цена относится к одному сеансу
        return sessions
