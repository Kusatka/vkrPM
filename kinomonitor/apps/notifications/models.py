from django.conf import settings
from django.db import models


class NotificationLog(models.Model):
    """Журнал отправленных уведомлений — защита от дублей."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Пользователь"
    )
    subscription = models.ForeignKey(
        "accounts.Subscription", on_delete=models.CASCADE, verbose_name="Подписка"
    )
    session = models.ForeignKey(
        "catalog.Session", on_delete=models.CASCADE, verbose_name="Сеанс"
    )
    text = models.TextField("Текст")
    sent_at = models.DateTimeField("Отправлено", auto_now_add=True)

    class Meta:
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"
        ordering = ["-sent_at"]

    def __str__(self):
        return f"{self.user} / {self.session} ({self.sent_at:%d.%m %H:%M})"


class TelegramState(models.Model):
    """Singleton: смещение getUpdates, чтобы не обрабатывать апдейты дважды."""

    last_update_id = models.BigIntegerField("Последний update_id", default=0)

    class Meta:
        verbose_name = "Состояние Telegram-бота"
        verbose_name_plural = "Состояние Telegram-бота"

    def __str__(self):
        return f"offset={self.last_update_id}"
