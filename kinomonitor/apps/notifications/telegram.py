import httpx
from django.conf import settings

API_BASE = "https://api.telegram.org/bot{token}/{method}"


def send_message(chat_id: str, text: str) -> bool:
    """Отправить сообщение. Без токена тихо выходит (удобно в dev)."""
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        return False
    resp = httpx.post(
        API_BASE.format(token=token, method="sendMessage"),
        json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
        timeout=10,
    )
    return resp.is_success


def get_updates(offset: int = 0) -> dict | None:
    """Получить апдейты бота (для привязки профилей по /start <код>)."""
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        return None
    resp = httpx.get(
        API_BASE.format(token=token, method="getUpdates"),
        params={"offset": offset, "timeout": 0},
        timeout=10,
    )
    return resp.json() if resp.is_success else None
