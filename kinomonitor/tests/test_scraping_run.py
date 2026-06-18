"""Тест устойчивости сбора: пустой прогон считается ошибкой (фикс №2)."""

from types import SimpleNamespace
from unittest import mock

import pytest

from apps.scraping import tasks
from apps.scraping.models import ScrapeRun


@pytest.mark.django_db
def test_run_parser_marks_empty_run_as_error():
    """0 собранных сеансов — ERROR в журнале, а не молчаливый SUCCESS."""

    def fake_parser():
        return SimpleNamespace(fetch_sessions=lambda: [])

    with mock.patch.object(tasks, "get_parser", return_value=fake_parser):
        tasks.run_parser("afisha")

    run = ScrapeRun.objects.get()
    assert run.status == ScrapeRun.Status.ERROR
    assert "0 сеансов" in run.error
