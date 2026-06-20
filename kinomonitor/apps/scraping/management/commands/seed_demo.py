"""Демо-данные + история цен для локального просмотра. Идемпотентна (не плодит данные)."""

import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.catalog.models import PriceSnapshot, Session
from apps.scraping import services
from apps.scraping.parsers.demo import DemoParser


class Command(BaseCommand):
    help = "Демо-данные (4 фильма, 3 кинотеатра) + история цен. Безопасно запускать повторно."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=5, help="Глубина истории цен, дней")
        parser.add_argument("--force", action="store_true", help="Пересоздать данные")

    def handle(self, *args, **opts):
        if Session.objects.exists() and PriceSnapshot.objects.exists() and not opts["force"]:
            self.stdout.write("Данные уже есть — пропускаю (для пересоздания: seed_demo --force).")
            return
        found = services.save_sessions(DemoParser().fetch_sessions())
        self.stdout.write(f"Сеансов засеяно: {found}")
        snaps = 0
        for session in Session.objects.all():
            base = 300 + random.randint(0, 150)
            for back in range(opts["days"], 0, -1):
                snap = PriceSnapshot.objects.create(
                    session=session, price_min=Decimal(base + random.randint(-40, 90))
                )
                PriceSnapshot.objects.filter(pk=snap.pk).update(
                    collected_at=timezone.now() - timedelta(days=back)
                )
                snaps += 1
        self.stdout.write(f"Снимков истории: {snaps}")
        self.stdout.write(self.style.SUCCESS("Готово. Запустите: python manage.py runserver"))
