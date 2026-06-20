"""Сбор РЕАЛЬНЫХ фильмов, кинотеатров и цен с сайтов-источников.

Это главный способ наполнить базу настоящими данными (в отличие от
seed_demo — тот кладёт 4 демо-фильма для офлайн-просмотра интерфейса).

    python manage.py scrape            # все источники (Афиша + Москино)
    python manage.py scrape moskino    # только указанные источники

Каждый источник опрашивается отдельно: ошибка/блокировка одного не
прерывает остальные. Каждый прогон пишется в журнал ScrapeRun (виден
в админке → «Запуски парсеров»). Нужен доступ в интернет.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.scraping import services
from apps.scraping.models import ScrapeRun
from apps.scraping.parsers import all_parsers, get_parser


class Command(BaseCommand):
    help = "Собрать реальные фильмы, кинотеатры и цены с Афиши и Москино."

    def add_arguments(self, parser):
        parser.add_argument(
            "sources",
            nargs="*",
            help="slug источников (afisha, moskino); по умолчанию — все.",
        )

    def handle(self, *args, **opts):
        available = [s for s in all_parsers() if s != "demo"]
        slugs = opts["sources"] or available

        total = 0
        for slug in slugs:
            if slug not in all_parsers():
                self.stderr.write(
                    self.style.ERROR(
                        f"Неизвестный источник «{slug}». Доступны: {', '.join(available)}."
                    )
                )
                continue

            run = ScrapeRun.objects.create(source=slug)
            self.stdout.write(f"[{slug}] сбор…")
            try:
                dtos = get_parser(slug)().fetch_sessions()
                count = services.save_sessions(dtos)
                run.sessions_found = count
                if count:
                    run.status = ScrapeRun.Status.SUCCESS
                    total += count
                    self.stdout.write(self.style.SUCCESS(f"[{slug}] сеансов: {count}"))
                else:
                    run.status = ScrapeRun.Status.ERROR
                    run.error = "0 сеансов: смена вёрстки источника или блокировка."
                    self.stderr.write(
                        self.style.WARNING(
                            f"[{slug}] 0 сеансов — проверьте доступ в интернет."
                        )
                    )
            except Exception as exc:  # noqa: BLE001 — журналируем и идём дальше
                run.status = ScrapeRun.Status.ERROR
                run.error = repr(exc)
                self.stderr.write(self.style.ERROR(f"[{slug}] ошибка: {exc!r}"))
            run.finished_at = timezone.now()
            run.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Готово. Всего обработано сеансов: {total}. "
                "Откройте сайт: python manage.py runserver"
            )
        )
