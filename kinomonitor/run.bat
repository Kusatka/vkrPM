@echo off
cd /d %~dp0
if not exist .env copy .env.example .env >nul
call .venv\Scripts\activate
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
