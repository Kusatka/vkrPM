"""Тесты улучшений: deep-link Telegram, спецпоказы, аналитика «когда покупать»."""

from datetime import timedelta
from decimal import Decimal
from unittest import mock

import pytest
from django.contrib.auth.models import User
from django.utils import timezone

from apps.accounts.models import Subscription, TelegramProfile
from apps.catalog.analytics import price_trend
from apps.catalog.models import Cinema, Movie, PriceSnapshot, Session, is_special_title
from apps.notifications import tasks
from apps.notifications.models import TelegramState

# --- спецпоказы ---

def test_special_title_detection():
    assert is_special_title("TheatreHD: «Зальцбург: Идиот»")
    assert is_special_title("Театр в кино: «Принц и нищий»")
    assert is_special_title("Иллюзион X Москва глазами инженера. Киносеанс и экскурсия")
    assert not is_special_title("Майкл")
    assert not is_special_title("Безумный Пьеро")


@pytest.mark.django_db
def test_special_movies_hidden_by_default(client):
    cinema = Cinema.objects.create(slug="c1", name="К1")
    starts = timezone.now() + timedelta(days=1)
    normal = Movie.objects.create(title="Майкл", year=2026)
    special = Movie.objects.create(title="TheatreHD: Норма", year=2026, is_special=True)
    for movie in (normal, special):
        Session.objects.create(cinema=cinema, movie=movie, starts_at=starts)

    page = client.get("/").content.decode()
    assert "Майкл" in page and "TheatreHD: Норма" not in page

    page = client.get("/?special=1").content.decode()
    assert "TheatreHD: Норма" in page and "спецпоказ" in page


# --- аналитика «когда покупать» ---

@pytest.fixture
def movie_with_history(db):
    cinema = Cinema.objects.create(slug="c2", name="К2")
    movie = Movie.objects.create(title="Фильм", year=2026)
    session = Session.objects.create(
        cinema=cinema, movie=movie, starts_at=timezone.now() + timedelta(days=2)
    )

    def add_snapshot(days_ago: int, price: str):
        snap = PriceSnapshot.objects.create(session=session, price_min=Decimal(price))
        PriceSnapshot.objects.filter(pk=snap.pk).update(
            collected_at=timezone.now() - timedelta(days=days_ago)
        )

    return movie, add_snapshot


@pytest.mark.django_db
def test_price_trend_rising(movie_with_history):
    movie, add_snapshot = movie_with_history
    add_snapshot(2, "300")
    add_snapshot(0, "400")
    trend = price_trend(movie)

    assert trend["direction"] == "rising"
    assert trend["change_pct"] == pytest.approx(33.3, abs=0.1)


@pytest.mark.django_db
def test_price_trend_falling_and_insufficient(movie_with_history):
    movie, add_snapshot = movie_with_history
    add_snapshot(0, "300")
    assert price_trend(movie) is None  # один день — мало данных

    add_snapshot(2, "400")
    assert price_trend(movie)["direction"] == "falling"


# --- deep-link Telegram ---

def fake_updates(code: str):
    return {
        "result": [
            {
                "update_id": 100,
                "message": {"chat": {"id": 777}, "text": f"/start {code}"},
            },
            {
                "update_id": 101,
                "message": {"chat": {"id": 888}, "text": "/start неизвестный-код"},
            },
        ]
    }


@pytest.mark.django_db
def test_poll_telegram_links_binds_profile():
    user = User.objects.create_user("tg-user", password="x")
    profile = TelegramProfile.objects.create(user=user)

    updates = fake_updates(profile.link_code)
    with (
        mock.patch.object(tasks.telegram, "get_updates", return_value=updates),
        mock.patch.object(tasks.telegram, "send_message", return_value=True) as send,
    ):
        assert tasks.poll_telegram_links() == 1

    profile.refresh_from_db()
    assert profile.chat_id == "777"
    assert profile.linked_at is not None
    assert TelegramState.objects.get(pk=1).last_update_id == 101
    send.assert_called_once()


@pytest.mark.django_db
def test_check_price_drops_uses_profile_chat_id():
    cinema = Cinema.objects.create(slug="c3", name="К3")
    movie = Movie.objects.create(title="Фильм3", year=2026)
    session = Session.objects.create(
        cinema=cinema, movie=movie, starts_at=timezone.now() + timedelta(days=1)
    )
    PriceSnapshot.objects.create(session=session, price_min=Decimal("200"))

    user = User.objects.create_user("u-prof", password="x")
    TelegramProfile.objects.create(user=user, chat_id="555")
    # chat_id в самой подписке пуст — должен взяться из профиля
    Subscription.objects.create(user=user, movie=movie, max_price=Decimal("500"))

    with mock.patch.object(tasks.telegram, "send_message", return_value=True) as send:
        assert tasks.check_price_drops() == 1
    assert send.call_args[0][0] == "555"


@pytest.mark.django_db
def test_subscriptions_page_shows_link_button(client, settings):
    settings.TELEGRAM_BOT_USERNAME = "kinomonitor_bot"
    User.objects.create_user("u-page", password="kino-Monitor-2026")
    client.login(username="u-page", password="kino-Monitor-2026")

    page = client.get("/accounts/subscriptions/").content.decode()
    profile = TelegramProfile.objects.get(user__username="u-page")
    assert f"https://t.me/kinomonitor_bot?start={profile.link_code}" in page
