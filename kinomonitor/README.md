# КиноМонитор

Сервис мониторинга цен кинотеатров Москвы. Выпускной проект цифровой кафедры.

Django 5 + DRF · Celery + Redis · PostgreSQL · HTMX + Chart.js.
План и архитектура: [`../docs/plan.md`](../docs/plan.md), деплой: [`../docs/deploy.md`](../docs/deploy.md).

## Источники данных

| Парсер | Что собирает |
|---|---|
| `afisha` | «Иллюзион» (Госфильмофонд) и «КАРО 11 Октябрь» со страниц кинотеатров на Афише.ру: цены «от N ₽», пометка SUB = показ в оригинале |
| `moskino` | Вся городская сеть «Москино» (~20 кинотеатров, включая «Юность», «Факел», «Салют») с mos-kino.ru/schedule: точные цены, пометка СУБ |
| `demo` | Генератор правдоподобных данных для разработки UI; не регистрируется по умолчанию |

Список кинотеатров для парсера `afisha` живёт в БД (админка → Кинотеатры →
галочка «Мониторим»). Раз в неделю задача `discover_cinemas` дописывает в БД
новые площадки из каталога Афиши (или вручную: `python manage.py
discover_cinemas`) — так сервис узнаёт о кинотеатрах, которых мы не знали.
Подробный разбор подсистемы: [`../docs/parsing.md`](../docs/parsing.md).

Селекторы парсеров сверены с реальными страницами 10.06.2026 и нарочно не
привязаны к CSS-классам (идут по текстовым токенам). После первого боевого
запуска проверь журнал в админке: **Сбор цен → Запуски парсеров**.

## Быстрый старт

```bash
cp .env.example .env
docker compose up --build -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

Собрать цены сейчас (иначе beat сам соберёт в течение 4 часов):

```bash
docker compose exec web python manage.py shell -c \
  "from apps.scraping.tasks import run_parser; run_parser('afisha'); run_parser('moskino')"
```

- http://localhost:8000 — афиша (фильтр «только в оригинале»)
- http://localhost:8000/admin — админка
- http://localhost:8000/api/ — REST API (DRF)

## Telegram-уведомления

1. Создать бота у @BotFather; в `.env` положить `TELEGRAM_BOT_TOKEN` и
   `TELEGRAM_BOT_USERNAME` (имя бота без @).
2. На странице «Мои подписки» нажать **«Привязать Telegram»** — откроется бот,
   после Start привязка происходит автоматически в течение минуты
   (задача `poll_telegram_links` ловит `/start <код>` и сохраняет chat_id).
3. Создать подписку с порогом цены — chat_id вручную указывать не нужно
   (поле осталось для переопределения; резервный путь — команда
   `python manage.py telegram_chat_id`).
4. `check_price_drops` шлёт сообщение, когда «цена от» опускается ниже порога;
   дубли отсекаются по `NotificationLog`.

## Настройка частоты сбора

`SCRAPE_INTERVAL_MINUTES` в `.env` (по умолчанию 240). Первые дни после деплоя
поставьте `60`, чтобы график истории быстрее наполнился, затем верните 240.
Спецпоказы (опера, TheatreHD, экскурсии) распознаются по названию и скрыты из
афиши по умолчанию — чекбокс «Спецпоказы» возвращает их в выдачу.

## Локально без Docker

```bash
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements-dev.txt
set DATABASE_URL=sqlite:///db.sqlite3
python manage.py migrate && python manage.py runserver
```

## Тесты и линтер

```bash
pytest        # 28 тестов: парсеры и discovery на фикстурах, подписки, Telegram, аналитика
ruff check .
```

## Как добавить новый источник цен

1. Создать класс в `apps/scraping/parsers/<источник>.py`, унаследовать `BaseParser`,
   заполнить `source_slug` и реализовать `fetch_sessions() -> list[SessionDTO]`.
2. Добавить импорт модуля в `apps/scraping/parsers/__init__.py`.
3. Сохранить HTML страницы в `tests/fixtures/` и написать тест разбора.

Реестр подхватит класс автоматически, beat начнёт запускать его каждые 4 часа.
