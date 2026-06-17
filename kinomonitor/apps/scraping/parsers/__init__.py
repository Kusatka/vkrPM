# Импорт модуля регистрирует парсер. Новый источник — добавить импорт сюда.
from . import afisha, moskino  # noqa: E402,F401
from .base import BaseParser, SessionDTO, all_parsers, get_parser

# demo-парсер не регистрируется по умолчанию (есть реальные источники);
# для наполнения тестовыми данными импортировать apps.scraping.parsers.demo.

__all__ = ["BaseParser", "SessionDTO", "all_parsers", "get_parser"]
