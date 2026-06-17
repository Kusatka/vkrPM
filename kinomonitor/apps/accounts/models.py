import uuid

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Q


class Subscription(models.Model):
    """Подписка пользователя: фильм и/или кинотеатр + порог цены."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscriptions",
        verbose_name="Пользователь",
    )
    movie = models.ForeignKey(
        "catalog.Movie",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name="Фильм",
    )
    cinema = models.ForeignKey(
        "catalog.Cinema",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name="Кинотеатр",
    )
    max_price = models.DecimalField("Порог цены, руб.", max_digits=8, decimal_places=2)
    telegram_chat_id = models.CharField("Telegram chat id", max_length=32, blank=True)
    is_active = models.BooleanField("Активна", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"
        constraints = [
            models.CheckConstraint(
                condition=Q(movie__isnull=False) | Q(cinema__isnull=False),
                name="subscription_has_target",
            ),
        ]

    def __str__(self):
        target = self.movie or self.cinema
        return f"{self.user}: {target} до {self.max_price} руб."

    @property
    def resolved_chat_id(self) -> str:
        """Куда слать: chat_id подписки, иначе — из привязанного Telegram-профиля."""
        if self.telegram_chat_id:
            return self.telegram_chat_id
        try:
            return self.user.telegram.chat_id
        except ObjectDoesNotExist:
            return ""


def make_link_code() -> str:
    return uuid.uuid4().hex


class TelegramProfile(models.Model):
    """Привязка Telegram через deep-link: t.me/<бот>?start=<link_code>."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="telegram",
        verbose_name="Пользователь",
    )
    chat_id = models.CharField("Telegram chat id", max_length=32, blank=True)
    link_code = models.CharField(
        "Код привязки", max_length=32, unique=True, default=make_link_code, editable=False
    )
    linked_at = models.DateTimeField("Привязан", null=True, blank=True)

    class Meta:
        verbose_name = "Telegram-профиль"
        verbose_name_plural = "Telegram-профили"

    def __str__(self):
        status = "привязан" if self.chat_id else "не привязан"
        return f"{self.user}: {status}"
