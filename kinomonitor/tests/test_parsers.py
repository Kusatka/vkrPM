"""Тесты парсеров на сохранённых фикстурах (день 10 плана).

Фикстуры воспроизводят текстовую структуру реальных страниц
(сверена 10.06.2026); селекторы не зависят от CSS-классов.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path

from apps.scraping.parsers.afisha import DEFAULT_CINEMAS, AfishaParser
from apps.scraping.parsers.moskino import MoskinoParser

FIXTURES = Path(__file__).parent / "fixtures"
DAY = date(2026, 6, 11)


def load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class TestAfishaParser:
    def parse(self):
        illusion = DEFAULT_CINEMAS[0]
        return AfishaParser().parse_day(load("afisha_day.html"), illusion, DAY)

    def test_sessions_count(self):
        # 4 сеанса «Майкла» + 1 «Ла-Ла Ленда»; фильм без сеансов пропущен
        assert len(self.parse()) == 5

    def test_prices_and_sub(self):
        sessions = self.parse()
        michael = [s for s in sessions if s.movie_title == "Майкл"]
        by_time = {s.starts_at.strftime("%H:%M"): s for s in michael}

        assert by_time["20:30"].price_min == Decimal("2000")
        assert by_time["20:30"].original_language is False
        assert by_time["10:00"].price_min == Decimal("150")
        assert by_time["10:00"].original_language is True  # 2D, SUB
        assert by_time["18:30"].price_min is None  # «Нет билетов»

    def test_split_sub_badge_and_thousands(self):
        lalaland = [s for s in self.parse() if s.movie_title == "Ла-Ла Ленд"]
        assert len(lalaland) == 1
        assert lalaland[0].original_language is True  # отдельный бейдж SUB
        assert lalaland[0].price_min == Decimal("2000")  # «от 2 000 ₽»
        assert lalaland[0].movie_year == 2016

    def test_cinema_attrs(self):
        s = self.parse()[0]
        assert s.cinema_slug == "illusion"
        assert s.cinema_is_niche is True


class TestMoskinoParser:
    def parse(self):
        return MoskinoParser().parse_schedule(load("moskino_schedule.html"), DAY)

    def test_sessions_count(self):
        assert len(self.parse()) == 7

    def test_cinema_attribution(self):
        sessions = self.parse()
        saturn = [s for s in sessions if s.cinema_slug == "moskino-saturn"]
        yunost = [s for s in sessions if s.cinema_slug == "moskino-yunost"]
        assert len(saturn) == 4
        assert len(yunost) == 3

    def test_movie_parsing(self):
        sessions = self.parse()
        obsession = [s for s in sessions if s.movie_title == "Обсессия"]
        assert obsession[0].movie_year == 2025
        assert {s.original_language for s in obsession} == {True, False}

        no_year = [s for s in sessions if s.movie_title == "Падшие ангелы"]
        assert no_year[0].movie_year is None

        quoted = [s for s in sessions if s.movie_title == "Питер FM"]
        assert quoted[0].movie_year == 2006  # кавычки-ёлочки срезаны

    def test_price_and_format(self):
        s = [x for x in self.parse() if x.starts_at.strftime("%H:%M") == "10:50"][0]
        assert s.price_min == s.price_max == Decimal("190")
        assert s.format == "2D"
        assert s.cinema_network == "Москино"
