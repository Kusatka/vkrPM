"""Тесты пользовательских сценариев: регистрация, подписки, уведомления, страницы."""

from datetime import timedelta
from decimal import Decimal
from unittest import mock

import pytest
from django.contrib.auth.models import User
from django.utils import timezone

from apps.accounts.models import Subscription
from apps.catalog.models import Cinema, Movie, PriceSnapshot, Session
from apps.notifications import tasks
from apps.notifications.models import NotificationLog

PASSWORD = "kino-Monitor-2026"


@pytest.fixture
def session(db):
    cinema, _ = Cinema.objects.get_or_create(
        slug="illusion", defaults={"name": "Иллюзион", "is_niche": True}
    )
    movie = Movie.objects.create(title="Майкл", original_title="Michael", year=2026)
    s = Session.objects.create(
        cinema=cinema,
        movie=movie,
        starts_at=timezone.now() + timedelta(days=1),
        original_language=True,
    )
    PriceSnapshot.objects.create(session=s, price_min=Decimal("300"))
    return s


@pytest.mark.django_db
def test_register_subscribe_delete_flow(client, session):
    resp = client.post(
        "/accounts/register/",
        {"username": "kusatka", "password1": PASSWORD, "password2": PASSWORD},
    )
    assert resp.status_code == 302  # залогинен и перенаправлен

    resp = client.post(
        "/accounts/subscriptions/",
        {"movie": session.movie_id, "max_price": "500", "telegram_chat_id": "42"},
    )
    assert resp.status_code == 302
    sub = Subscription.objects.get()
    assert sub.user.username == "kusatka"

    resp = client.post(f"/accounts/subscriptions/{sub.pk}/delete/")
    assert Subscription.objects.count() == 0


@pytest.mark.django_db
def test_subscription_requires_target(client):
    User.objects.create_user("u2", password=PASSWORD)
    client.login(username="u2", password=PASSWORD)
    resp = client.post(
        "/accounts/subscriptions/", {"max_price": "500", "telegram_chat_id": "42"}
    )
    assert resp.status_code == 200  # форма с ошибкой, подписка не создана
    assert Subscription.objects.count() == 0


@pytest.mark.django_db
def test_check_price_drops_sends_once(session):
    user = User.objects.create_user("u3", password=PASSWORD)
    Subscription.objects.create(
        user=user,
        movie=session.movie,
        max_price=Decimal("500"),
        telegram_chat_id="42",
    )
    with mock.patch(
        "apps.notifications.tasks.telegram.send_message", return_value=True
    ) as send:
        assert tasks.check_price_drops() == 1
        assert send.call_count == 1
        assert NotificationLog.objects.count() == 1
        # повторный запуск не шлёт дубль
        assert tasks.check_price_drops() == 0
        assert send.call_count == 1


@pytest.mark.django_db
def test_no_notification_above_threshold(session):
    user = User.objects.create_user("u4", password=PASSWORD)
    Subscription.objects.create(
        user=user,
        movie=session.movie,
        max_price=Decimal("100"),  # порог ниже текущей цены 300
        telegram_chat_id="42",
    )
    with mock.patch(
        "apps.notifications.tasks.telegram.send_message", return_value=True
    ) as send:
        assert tasks.check_price_drops() == 0
        send.assert_not_called()


@pytest.mark.django_db
def test_pages_render(client, session):
    assert client.get("/").status_code == 200
    assert client.get("/?original=1").status_code == 200
    resp = client.get(f"/movie/{session.movie_id}/")
    assert resp.status_code == 200
    assert "Иллюзион".encode() in resp.content


@pytest.mark.django_db
def test_movie_list_shows_current_not_historical_min(client):
    """«Цена от» = актуальная цена, а не исторический минимум по всем снимкам (фикс №1)."""
    cinema = Cinema.objects.create(slug="cur", name="Курская")
    movie = Movie.objects.create(title="Тестовый фильм", year=2026)
    s = Session.objects.create(
        cinema=cinema, movie=movie, starts_at=timezone.now() + timedelta(days=1)
    )
    # неделю назад было 200, сейчас 450 — показать должны 450
    old = PriceSnapshot.objects.create(session=s, price_min=Decimal("200"))
    PriceSnapshot.objects.filter(pk=old.pk).update(
        collected_at=timezone.now() - timedelta(days=7)
    )
    PriceSnapshot.objects.create(session=s, price_min=Decimal("450"))

    page = client.get("/").content.decode()
    assert "450 руб." in page
    assert "200 руб." not in page
