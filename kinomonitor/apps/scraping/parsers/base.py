"""Базовый интерфейс парсера-адаптера.

Каждый источник цен — отдельный класс-наследник BaseParser.
Наследники регистрируются в реестре автоматически (см. __init_subclass__),
добавление нового источника не требует изменений в ядре.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


class ParserBlocked(Exception):
    """Источник ответил кодом блокировки (403/429/503). Поднимаем исключение,
    чтобы прогон попал в журнал как ошибка и сработал повтор, а не молчаливый
    «успех с 0 сеансов»."""


@dataclass
class SessionDTO:
    """Нормализованный сеанс из любого источника."""

    cinema_slug: str
    cinema_name: str
    movie_title: str
    starts_at: datetime  # обязательно aware (с таймзоной)
    price_min: Decimal | None
    price_max: Decimal | None = None
    movie_original_title: str = ""
    movie_year: int | None = None
    format: str = "2D"
    original_language: bool = False
    hall: str = ""
    cinema_network: str = ""
    cinema_is_niche: bool = False


_REGISTRY: dict[str, type["BaseParser"]] = {}


class BaseParser(ABC):
    source_slug: str = ""  # короткий код источника, например "illusion"
    source_name: str = ""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.source_slug:
            _REGISTRY[cls.source_slug] = cls

    @abstractmethod
    def fetch_sessions(self) -> list[SessionDTO]:
        """Вернуть будущие сеансы источника с ценами."""


def get_parser(slug: str) -> type[BaseParser]:
    return _REGISTRY[slug]


def all_parsers() -> dict[str, type[BaseParser]]:
    return dict(_REGISTRY)
