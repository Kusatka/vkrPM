"""Demo-парсер: наполняет БД правдоподобными данными, пока нет реальных парсеров.

Нужен, чтобы UI, графики и уведомления можно было разрабатывать с первого дня.
УДАЛИТЬ после появления реальных парсеров (день 4–5) — убрать импорт в __init__.py.
"""

import random
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.utils import timezone

from .base import BaseParser, SessionDTO

CINEMAS = [
    ("illusion", "Иллюзион", "Госфильмофонд", True),
    ("karo-oktyabr", "КАРО 11 Октябрь", "Каро", False),
    ("moskino-zvezda", "Звезда (Москино)", "Москино", True),
]

MOVIES = [
    ("Майкл", "Michael", 2026, True, Decimal("450")),
    ("Безумный Пьеро", "Pierrot le fou", 1965, True, Decimal("300")),
    ("Холоп 3", "", 2026, False, Decimal("550")),
    ("Ла-Ла Ленд", "La La Land", 2016, True, Decimal("400")),
]

SHOW_TIMES = [time(12, 0), time(18, 30), time(21, 0)]


class DemoParser(BaseParser):
    source_slug = "demo"
    source_name = "Demo-данные"

    def fetch_sessions(self) -> list[SessionDTO]:
        result = []
        today = timezone.localdate()
        for day_offset in range(3):
            day = today + timedelta(days=day_offset + 1)
            for slug, cinema, network, niche in CINEMAS:
                for i, (title, orig, year, in_original, base) in enumerate(MOVIES):
                    # Стабильная в рамках дня псевдослучайная цена,
                    # меняется день ото дня — график получает динамику.
                    rnd = random.Random(f"{timezone.localdate()}{slug}{title}")
                    price = base + Decimal(rnd.choice([-50, 0, 50, 100]))
                    starts = timezone.make_aware(
                        datetime.combine(day, SHOW_TIMES[i % len(SHOW_TIMES)])
                    )
                    result.append(
                        SessionDTO(
                            cinema_slug=slug,
                            cinema_name=cinema,
                            cinema_network=network,
                            cinema_is_niche=niche,
                            movie_title=title,
                            movie_original_title=orig,
                            movie_year=year,
                            starts_at=starts,
                            price_min=price,
                            price_max=price + Decimal("200"),
                            original_language=in_original and niche,
                        )
                    )
        return result
