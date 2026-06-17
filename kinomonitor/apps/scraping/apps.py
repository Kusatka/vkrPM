from django.apps import AppConfig


class ScrapingConfig(AppConfig):
    name = "apps.scraping"
    verbose_name = "Сбор цен"

    def ready(self):
        # Импорт регистрирует все парсеры в реестре
        from . import parsers  # noqa: F401
