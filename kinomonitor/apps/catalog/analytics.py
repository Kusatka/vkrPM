"""Аналитика «когда покупать»: тренд цены по накопленной истории снимков."""

from datetime import timedelta

from django.utils import timezone

from .models import Movie, PriceSnapshot

WINDOW_DAYS = 5  # окно анализа
THRESHOLD_PCT = 3.0  # изменение меньше порога считаем «стабильно»


def price_trend(movie: Movie) -> dict | None:
    """Сравнить среднюю минимальную цену фильма по дням окна.

    Возвращает dict для шаблона (direction/change_pct/days/text/css)
    или None, если истории меньше двух дней.
    """
    since = timezone.now() - timedelta(days=WINDOW_DAYS)
    rows = PriceSnapshot.objects.filter(
        session__movie=movie, collected_at__gte=since
    ).values_list("collected_at", "price_min")

    by_day: dict = {}
    for collected_at, price in rows:
        day = timezone.localtime(collected_at).date()
        by_day.setdefault(day, []).append(float(price))
    if len(by_day) < 2:
        return None

    days = sorted(by_day)
    first = sum(by_day[days[0]]) / len(by_day[days[0]])
    last = sum(by_day[days[-1]]) / len(by_day[days[-1]])
    if first <= 0:
        return None
    change = (last - first) / first * 100

    if change > THRESHOLD_PCT:
        direction, text, css = "rising", "Цена растёт — выгоднее купить сейчас", "alert-warning"
    elif change < -THRESHOLD_PCT:
        direction, text, css = "falling", "Цена снижается — можно подождать", "alert-success"
    else:
        direction, text, css = "stable", "Цена стабильна", "alert-secondary"
    return {
        "direction": direction,
        "change_pct": round(change, 1),
        "days": (days[-1] - days[0]).days + 1,
        "text": text,
        "css": css,
    }
