"""Смоук-тесты каркаса: нормализация, реестр парсеров, пайплайн сохранения."""

import pytest

from apps.catalog.models import Movie, PriceSnapshot, normalize_title
from apps.scraping import services
from apps.scraping.parsers import (
    all_parsers,
    demo,  # noqa: F401 — регистрирует demo-парсер
    get_parser,
)


def test_normalize_title():
    assert normalize_title("Дюна: Часть вторая") == normalize_title("дюна — часть Вторая!")


def test_parsers_registered():
    assert {"afisha", "moskino", "demo"} <= set(all_parsers())


@pytest.mark.django_db
def test_demo_pipeline_saves_sessions():
    dtos = get_parser("demo")().fetch_sessions()
    processed = services.save_sessions(dtos)

    assert processed == len(dtos) > 0
    assert Movie.objects.exists()
    assert PriceSnapshot.objects.exists()


@pytest.mark.django_db
def test_pipeline_skips_unchanged_prices():
    dtos = get_parser("demo")().fetch_sessions()
    services.save_sessions(dtos)
    count_after_first = PriceSnapshot.objects.count()
    services.save_sessions(dtos)  # повторный прогон с теми же ценами

    assert PriceSnapshot.objects.count() == count_after_first
