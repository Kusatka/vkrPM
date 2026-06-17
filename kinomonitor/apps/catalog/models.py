import re

from django.db import models

SPECIAL_TITLE_RE = re.compile(
    r"theatrehd|театр в кино|спецпоказ|премьера|экскурси|лектори|опера|балет|концерт",
    re.IGNORECASE,
)


def is_special_title(title: str) -> bool:
    """Спецпоказ (опера, балет, экскурсия, TheatreHD) — не обычный кинопрокат."""
    return bool(SPECIAL_TITLE_RE.search(title))


def normalize_title(title: str) -> str:
    """Нормализация названия для матчинга фильмов между источниками."""
    t = title.lower().replace("ё", "е")
    t = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


class Cinema(models.Model):
    slug = models.SlugField("Код", unique=True)
    name = models.CharField("Название", max_length=200)
    network = models.CharField("Сеть", max_length=100, blank=True)
    city = models.CharField("Город", max_length=100, default="Москва")
    address = models.CharField("Адрес", max_length=300, blank=True)
    website = models.URLField("Сайт", blank=True)
    is_niche = models.BooleanField(
        "Нишевый",
        default=False,
        help_text="Артхаус, ретроспективы, показы на языке оригинала",
    )
    afisha_slug = models.CharField(
        "Слаг на Афише.ру",
        max_length=200,
        blank=True,
        help_text="Например, illyuzion-2692; заполняется автообнаружением",
    )
    is_monitored = models.BooleanField(
        "Мониторим",
        default=False,
        help_text="Опрашивать этот кинотеатр парсером afisha",
    )

    class Meta:
        verbose_name = "Кинотеатр"
        verbose_name_plural = "Кинотеатры"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Movie(models.Model):
    title = models.CharField("Название", max_length=300)
    original_title = models.CharField("Оригинальное название", max_length=300, blank=True)
    year = models.PositiveSmallIntegerField("Год", null=True, blank=True)
    normalized_title = models.CharField(max_length=300, db_index=True, editable=False)
    is_special = models.BooleanField(
        "Спецпоказ",
        default=False,
        help_text="Опера, балет, TheatreHD, экскурсии — исключается из афиши по умолчанию",
    )

    class Meta:
        verbose_name = "Фильм"
        verbose_name_plural = "Фильмы"
        ordering = ["title"]
        constraints = [
            models.UniqueConstraint(
                fields=["normalized_title", "year"], name="uniq_movie_title_year"
            ),
        ]

    def __str__(self):
        return f"{self.title} ({self.year})" if self.year else self.title

    def save(self, *args, **kwargs):
        self.normalized_title = normalize_title(self.title)
        super().save(*args, **kwargs)


class Session(models.Model):
    class Format(models.TextChoices):
        F2D = "2D", "2D"
        F3D = "3D", "3D"
        IMAX = "IMAX", "IMAX"
        OTHER = "OTHER", "Другое"

    cinema = models.ForeignKey(
        Cinema, on_delete=models.CASCADE, related_name="sessions", verbose_name="Кинотеатр"
    )
    movie = models.ForeignKey(
        Movie, on_delete=models.CASCADE, related_name="sessions", verbose_name="Фильм"
    )
    starts_at = models.DateTimeField("Начало сеанса", db_index=True)
    format = models.CharField(
        "Формат", max_length=10, choices=Format.choices, default=Format.F2D
    )
    original_language = models.BooleanField("На языке оригинала", default=False)
    hall = models.CharField("Зал", max_length=100, blank=True)

    class Meta:
        verbose_name = "Сеанс"
        verbose_name_plural = "Сеансы"
        ordering = ["starts_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["cinema", "movie", "starts_at", "format"], name="uniq_session"
            ),
        ]

    def __str__(self):
        return f"{self.movie} — {self.cinema} {self.starts_at:%d.%m %H:%M}"

    @property
    def latest_price(self):
        return self.prices.order_by("-collected_at").first()


class PriceSnapshot(models.Model):
    session = models.ForeignKey(
        Session, on_delete=models.CASCADE, related_name="prices", verbose_name="Сеанс"
    )
    price_min = models.DecimalField("Мин. цена, руб.", max_digits=8, decimal_places=2)
    price_max = models.DecimalField(
        "Макс. цена, руб.", max_digits=8, decimal_places=2, null=True, blank=True
    )
    collected_at = models.DateTimeField("Собрано", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Снимок цены"
        verbose_name_plural = "Снимки цен"
        ordering = ["-collected_at"]
        indexes = [models.Index(fields=["session", "collected_at"])]

    def __str__(self):
        return f"{self.session_id}: от {self.price_min} ({self.collected_at:%d.%m %H:%M})"
