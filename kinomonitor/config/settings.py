"""Настройки проекта Вотчер."""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, True))
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="dev-only-insecure-key")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "apps.catalog",
    "apps.scraping",
    "apps.accounts",
    "apps.notifications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": env.db("DATABASE_URL", default="postgres://kino:kino@db:5432/kino"),
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}

# Интервал сбора цен, минуты. Первые дни после деплоя стоит поставить 60,
# чтобы график истории быстрее наполнился, затем вернуть 240.
SCRAPE_INTERVAL_MINUTES = env.int("SCRAPE_INTERVAL_MINUTES", default=240)
TELEGRAM_POLL_SECONDS = env.int("TELEGRAM_POLL_SECONDS", default=60)

# --- Celery ---
CELERY_BROKER_URL = env("REDIS_URL", default="redis://redis:6379/0")
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    "scrape-all-sources": {
        "task": "apps.scraping.tasks.run_all_parsers",
        "schedule": 60 * SCRAPE_INTERVAL_MINUTES,
    },
    "check-price-drops": {
        "task": "apps.notifications.tasks.check_price_drops",
        "schedule": 60 * SCRAPE_INTERVAL_MINUTES,
    },
    "poll-telegram-links": {
        "task": "apps.notifications.tasks.poll_telegram_links",
        "schedule": TELEGRAM_POLL_SECONDS,
    },
    "discover-cinemas": {
        "task": "apps.scraping.tasks.discover_cinemas",
        "schedule": 60 * 60 * 24 * 7,  # раз в неделю
    },
}

# --- Парсинг и уведомления ---
TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN", default="")
TELEGRAM_BOT_USERNAME = env("TELEGRAM_BOT_USERNAME", default="")
SCRAPE_DAYS_AHEAD = env.int("SCRAPE_DAYS_AHEAD", default=3)
SCRAPER_USER_AGENT = env(
    "SCRAPER_USER_AGENT",
    default="WatcherBot/0.1 (uchebnyi proekt tsifrovoi kafedry)",
)
# Пауза между HTTP-запросами парсера, секунды: не выглядеть ботом и не словить
# блокировку при последовательном опросе многих кинотеатров.
SCRAPER_DELAY_SECONDS = env.float("SCRAPER_DELAY_SECONDS", default=1.0)
