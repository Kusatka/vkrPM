# Деплой (день 11 плана)

Подойдёт любой VPS с Ubuntu 22+ (1 vCPU / 1–2 ГБ RAM достаточно).

```bash
# на сервере
apt update && apt install -y docker.io docker-compose-v2 git
git clone <репозиторий> && cd kinomonitor
cp .env.example .env
```

В `.env` для прода:

```
DEBUG=0
SECRET_KEY=<длинный случайный>
ALLOWED_HOSTS=ваш-домен.ru,IP-сервера
TELEGRAM_BOT_TOKEN=<токен>
TELEGRAM_BOT_USERNAME=<имя бота без @>
SCRAPE_INTERVAL_MINUTES=60   # первые дни — час, потом вернуть 240
```

В `docker-compose.yml` для сервиса `web` заменить команду на gunicorn:

```yaml
command: sh -c "python manage.py migrate && python manage.py collectstatic --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000"
```

Запуск: `docker compose up --build -d`. Статику отдаёт WhiteNoise,
отдельный nginx не обязателен (для защиты диплома достаточно порта 8000
или простейшего проксирования через Caddy: `caddy reverse-proxy --from домен --to :8000`).

Проверка после запуска: админка → «Запуски парсеров» (статус success),
страница фильма — график наполняется с каждым прогоном beat (4 ч).

Важно: чтобы к защите была история цен, развернуть как можно раньше —
каждый день работы beat = новая точка на графике.
