"""Утилита привязки Telegram: показывает chat_id всех, кто написал боту."""

import httpx
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Показать chat_id пользователей, написавших боту (для поля подписки)"

    def handle(self, *args, **options):
        token = settings.TELEGRAM_BOT_TOKEN
        if not token:
            self.stderr.write("TELEGRAM_BOT_TOKEN не задан в .env")
            return
        resp = httpx.get(
            f"https://api.telegram.org/bot{token}/getUpdates", timeout=10
        )
        chats = {}
        for upd in resp.json().get("result", []):
            chat = (upd.get("message") or {}).get("chat") or {}
            if chat.get("id"):
                chats[chat["id"]] = chat.get("username") or chat.get("first_name", "")
        if not chats:
            self.stdout.write("Обновлений нет: напишите боту /start и повторите.")
        for chat_id, name in chats.items():
            self.stdout.write(f"{chat_id}\t{name}")
