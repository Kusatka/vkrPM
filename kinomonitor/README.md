# Вотчер

Учебный проект по курсу «Фронтенд и бэкенд разработка».

Сервис мониторинга цен и расписания киносеансов в кинотеатрах Москвы. Собирает
расписание и цены с сайтов кинотеатров, хранит историю цен и показывает, где и
когда дешевле. Отдельно выделяет показы в оригинале.

## Стек

- Python, Django, Django REST Framework
- SQLite (локально) / PostgreSQL
- Парсинг: httpx + BeautifulSoup
- Фронтенд: Bootstrap, HTMX, Chart.js
- Дополнительно: Celery + Redis, Docker, Telegram-бот
- Тесты: pytest, ruff

## Запуск

Первый раз:

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env
```

В файле `.env` указать базу: `DATABASE_URL=sqlite:///db.sqlite3`. Дальше:

```
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo
python manage.py runserver
```

Потом для обычного запуска хватает `python manage.py runserver`.

Адреса:

- `http://localhost:8000` — афиша
- `/new/` — новинки
- `/admin/` — админка
- `/api/` — REST API

## Данные

- `python manage.py seed_demo` — демо-данные для просмотра интерфейса.
- `python manage.py scrape` — собрать реальные фильмы и цены с Афиши и Москино
  (нужен интернет). Каждый прогон виден в админке → «Запуски парсеров».

## Что умеет

- Афиша карточками: поиск, фильтр «только в оригинале», страница «Новинки».
- Страница фильма: сравнение цен по кинотеатрам, график истории цены и
  подсказка «когда покупать».
- Регистрация, подписки на фильм с порогом цены, уведомления в Telegram.
- Админка и REST API.

## Тесты

```
pytest
ruff check .
```
