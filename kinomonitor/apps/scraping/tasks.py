from celery import shared_task
from django.utils import timezone

from . import services
from .models import ScrapeRun
from .parsers import all_parsers, get_parser


@shared_task
def discover_cinemas() -> int:
    """Еженедельно дописывает в БД кинотеатры из каталога Афиши (см. discovery.py)."""
    from . import discovery

    return discovery.sync_cinemas()


@shared_task
def run_all_parsers():
    """Запустить каждый источник отдельной задачей: падение одного не валит остальные."""
    for slug in all_parsers():
        run_parser.delay(slug)


@shared_task(bind=True, max_retries=2, default_retry_delay=300)
def run_parser(self, slug: str) -> int:
    run = ScrapeRun.objects.create(source=slug)
    try:
        dtos = get_parser(slug)().fetch_sessions()
        run.sessions_found = services.save_sessions(dtos)
        if run.sessions_found == 0:
            # 0 сеансов по всем кинотеатрам и дням — почти наверняка смена вёрстки
            # источника или блокировка, а не реальное отсутствие сеансов.
            run.status = ScrapeRun.Status.ERROR
            run.error = (
                "Получено 0 сеансов: вероятна смена вёрстки источника или блокировка."
            )
        else:
            run.status = ScrapeRun.Status.SUCCESS
    except Exception as exc:
        run.status = ScrapeRun.Status.ERROR
        run.error = repr(exc)
        run.finished_at = timezone.now()
        run.save()
        raise self.retry(exc=exc)
    run.finished_at = timezone.now()
    run.save()
    return run.sessions_found
