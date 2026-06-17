"""Общий пайплайн сохранения: DTO парсера -> модели каталога."""

from apps.catalog.models import (
    Cinema,
    Movie,
    PriceSnapshot,
    Session,
    is_special_title,
    normalize_title,
)

from .parsers.base import SessionDTO


def save_sessions(dtos: list[SessionDTO]) -> int:
    """Upsert кинотеатров/фильмов/сеансов; снимок цены — только при её изменении.

    Возвращает число обработанных сеансов.
    """
    processed = 0
    for dto in dtos:
        cinema, _ = Cinema.objects.get_or_create(
            slug=dto.cinema_slug,
            defaults={
                "name": dto.cinema_name,
                "network": dto.cinema_network,
                "is_niche": dto.cinema_is_niche,
            },
        )
        movie, _ = Movie.objects.get_or_create(
            normalized_title=normalize_title(dto.movie_title),
            year=dto.movie_year,
            defaults={
                "title": dto.movie_title,
                "original_title": dto.movie_original_title,
                "is_special": is_special_title(dto.movie_title),
            },
        )
        session, _ = Session.objects.get_or_create(
            cinema=cinema,
            movie=movie,
            starts_at=dto.starts_at,
            format=dto.format,
            defaults={"original_language": dto.original_language, "hall": dto.hall},
        )
        processed += 1
        if dto.price_min is None:
            continue
        last = session.prices.order_by("-collected_at").first()
        if last and last.price_min == dto.price_min and last.price_max == dto.price_max:
            continue  # цена не изменилась — не плодим одинаковые снимки
        PriceSnapshot.objects.create(
            session=session, price_min=dto.price_min, price_max=dto.price_max
        )
    return processed
