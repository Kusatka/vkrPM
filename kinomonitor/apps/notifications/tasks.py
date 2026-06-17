from celery import shared_task
from django.utils import timezone

from apps.accounts.models import Subscription, TelegramProfile
from apps.catalog.models import Session

from . import telegram
from .models import NotificationLog, TelegramState


@shared_task
def poll_telegram_links() -> int:
    """Привязка Telegram по deep-link: ловим «/start <код>» через getUpdates.

    Пользователь жмёт кнопку на странице подписок -> попадает в бота ->
    Telegram сам отправляет /start с кодом -> здесь находим профиль по коду
    и сохраняем chat_id. Возвращает число привязанных профилей.
    """
    data = telegram.get_updates(offset=_state().last_update_id + 1)
    if not data:
        return 0
    state = _state()
    linked = 0
    max_id = state.last_update_id
    for upd in data.get("result", []):
        max_id = max(max_id, upd.get("update_id", 0))
        msg = upd.get("message") or {}
        chat = msg.get("chat") or {}
        text = (msg.get("text") or "").strip()
        if not chat.get("id") or not text.startswith("/start"):
            continue
        parts = text.split(maxsplit=1)
        if len(parts) != 2:
            continue
        profile = TelegramProfile.objects.filter(link_code=parts[1].strip()).first()
        if profile is None:
            continue
        profile.chat_id = str(chat["id"])
        profile.linked_at = timezone.now()
        profile.save()
        telegram.send_message(
            profile.chat_id,
            f"Telegram привязан к аккаунту <b>{profile.user.username}</b>. "
            "Уведомления о снижении цен включены.",
        )
        linked += 1
    if max_id != state.last_update_id:
        state.last_update_id = max_id
        state.save()
    return linked


def _state() -> TelegramState:
    state, _ = TelegramState.objects.get_or_create(pk=1)
    return state


@shared_task
def check_price_drops() -> int:
    """Найти сеансы дешевле порога подписки и разослать уведомления."""
    now = timezone.now()
    sent = 0
    subs = Subscription.objects.filter(is_active=True).select_related(
        "movie", "cinema", "user"
    )
    for sub in subs:
        chat_id = sub.resolved_chat_id
        if not chat_id:
            continue
        sessions = Session.objects.filter(starts_at__gte=now)
        if sub.movie:
            sessions = sessions.filter(movie=sub.movie)
        if sub.cinema:
            sessions = sessions.filter(cinema=sub.cinema)
        for session in sessions.select_related("movie", "cinema")[:200]:
            price = session.latest_price
            if price is None or price.price_min > sub.max_price:
                continue
            if NotificationLog.objects.filter(subscription=sub, session=session).exists():
                continue
            text = (
                f"<b>{session.movie.title}</b>\n"
                f"{session.cinema.name}, {timezone.localtime(session.starts_at):%d.%m %H:%M}\n"
                f"Цена от {price.price_min:.0f} руб. (ваш порог {sub.max_price:.0f} руб.)"
            )
            if telegram.send_message(chat_id, text):
                NotificationLog.objects.create(
                    user=sub.user, subscription=sub, session=session, text=text
                )
                sent += 1
    return sent
