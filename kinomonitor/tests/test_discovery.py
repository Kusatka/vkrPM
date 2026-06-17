"""Тесты автообнаружения кинотеатров и конфигурации парсеров из БД."""

from pathlib import Path

import pytest

from apps.catalog.models import Cinema
from apps.scraping.discovery import parse_catalog
from apps.scraping.parsers.afisha import DEFAULT_CINEMAS, monitored_cinemas
from apps.scraping.parsers.moskino import MoskinoParser

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_catalog():
    found = parse_catalog((FIXTURES / "afisha_cinema_list.html").read_text(encoding="utf-8"))

    assert found["pioner-2836"] == "Пионер"
    assert found["hudozhestvenniy-2959"] == "Художественный"
    # ссылки на метро и разделы не считаются кинотеатрами
    assert len(found) == 4


@pytest.mark.django_db
def test_monitored_cinemas_from_db():
    # сид-миграция включает мониторинг двух стартовых кинотеатров
    slugs = {c.slug for c in monitored_cinemas()}
    assert slugs == {"illusion", "karo-oktyabr"}

    # «обнаруженный» кинотеатр появляется в опросе после галочки в админке
    Cinema.objects.create(
        slug="afisha-2836", name="Пионер", afisha_slug="pioner-2836", is_monitored=True
    )
    assert "afisha-2836" in {c.slug for c in monitored_cinemas()}


def test_monitored_cinemas_fallback_without_db():
    # без доступа к БД (нет маркера django_db) — встроенный список
    assert monitored_cinemas() == list(DEFAULT_CINEMAS)


@pytest.mark.django_db
def test_moskino_map_extends_from_db():
    Cinema.objects.create(slug="moskino-zvezda", name="Звезда (Москино)", network="Москино")
    mapping = MoskinoParser()._cinema_map()

    assert mapping["Звезда"] == "moskino-zvezda"
    assert mapping["Юность"] == "moskino-yunost"  # встроенный список сохранился
