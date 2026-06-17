"""Автообнаружение кинотеатров — решение проблемы «мы знаем не все площадки».

Каталог Афиши.ру перечисляет все кинотеатры Москвы ссылками вида
/msk/cinema/<slug>-<id>/. Задача discover_cinemas (раз в неделю) добавляет
неизвестные площадки в БД с is_monitored=False. Включение мониторинга —
галочка в админке; парсер afisha подхватит кинотеатр без правки кода.
"""

import re

import httpx
from bs4 import BeautifulSoup
from django.conf import settings

CATALOG_URL = "https://www.afisha.ru/msk/cinema/cinema_list/"
CINEMA_HREF = re.compile(r"/msk/cinema/(?P<slug>[a-z0-9-]+-(?P<id>\d+))/?$")


def parse_catalog(html: str) -> dict[str, str]:
    """Вернуть {afisha_slug: название} из HTML каталога кинотеатров."""
    soup = BeautifulSoup(html, "lxml")
    found: dict[str, str] = {}
    for a in soup.find_all("a", href=CINEMA_HREF):
        name = a.get_text(" ", strip=True)
        if not name or name.startswith("/"):
            continue  # ссылка-постер или служебный текст
        m = CINEMA_HREF.search(a["href"])
        found.setdefault(m["slug"], name)
    return found


def sync_cinemas() -> int:
    """Дописать в БД кинотеатры, которых ещё нет. Возвращает число новых."""
    from apps.catalog.models import Cinema

    resp = httpx.get(
        CATALOG_URL,
        headers={"User-Agent": settings.SCRAPER_USER_AGENT},
        timeout=15,
        follow_redirects=True,
    )
    resp.raise_for_status()
    created = 0
    for afisha_slug, name in parse_catalog(resp.text).items():
        afisha_id = afisha_slug.rsplit("-", 1)[-1]
        _, was_created = Cinema.objects.get_or_create(
            afisha_slug=afisha_slug,
            defaults={
                "slug": f"afisha-{afisha_id}",
                "name": name,
                "network": "Каро" if name.lower().startswith("каро") else "",
            },
        )
        created += int(was_created)
    return created
