from django.db import models


class ScrapeRun(models.Model):
    class Status(models.TextChoices):
        RUNNING = "running", "Выполняется"
        SUCCESS = "success", "Успех"
        ERROR = "error", "Ошибка"

    source = models.CharField("Источник", max_length=50, db_index=True)
    status = models.CharField(
        "Статус", max_length=10, choices=Status.choices, default=Status.RUNNING
    )
    started_at = models.DateTimeField("Запущен", auto_now_add=True)
    finished_at = models.DateTimeField("Завершён", null=True, blank=True)
    sessions_found = models.PositiveIntegerField("Сеансов обработано", default=0)
    error = models.TextField("Ошибка", blank=True)

    class Meta:
        verbose_name = "Запуск парсера"
        verbose_name_plural = "Запуски парсеров"
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.source} [{self.status}] {self.started_at:%d.%m %H:%M}"
