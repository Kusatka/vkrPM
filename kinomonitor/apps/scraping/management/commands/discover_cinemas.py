from django.core.management.base import BaseCommand

from apps.scraping.discovery import sync_cinemas


class Command(BaseCommand):
    help = "Найти на Афише.ру кинотеатры, которых нет в БД, и добавить их"

    def handle(self, *args, **options):
        created = sync_cinemas()
        self.stdout.write(f"Добавлено новых кинотеатров: {created}")
        self.stdout.write("Включить мониторинг: админка → Кинотеатры → галочка «Мониторим».")
