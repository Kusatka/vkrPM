@echo off
chcp 65001 >nul
cd /d %~dp0
if not exist .env copy .env.example .env >nul
call .venv\Scripts\activate
echo Сбор реальных фильмов и цен (Афиша + Москино). Нужен интернет...
python manage.py scrape
echo.
echo Готово. Откройте сайт через run.bat или: python manage.py runserver
pause
