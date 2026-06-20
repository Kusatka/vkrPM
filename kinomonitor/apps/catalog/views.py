from collections import defaultdict

from django.db.models import Min, OuterRef, Subquery
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .analytics import price_trend
from .models import Movie, PriceSnapshot, Session

# Однотонные цвета постеров-заглушек (реальных афиш нет) — сепия-кино-палитра.
POSTER_COLORS = ["#a8551f", "#7c2d22", "#5b6e2c", "#46402f", "#8a6d3b", "#6b4a2a"]
# Цвета линий графика «цена по кинотеатрам».
CHART_COLORS = ["#a8551f", "#5b6e2c", "#185fa5", "#7c2d22", "#8a6d3b", "#46402f", "#6b4a2a"]


def _attach_min_prices(movies, now, only_original=False):
    """Проставить каждому фильму актуальную мин. цену, флаг оригинала и цвет постера.

    Минимум считается по ПОСЛЕДНИМ снимкам будущих сеансов (а не по всей истории
    цен), поэтому отображается актуальная цена, а не исторический минимум.
    """
    latest_price = (
        PriceSnapshot.objects.filter(session=OuterRef("pk"))
        .order_by("-collected_at")
        .values("price_min")[:1]
    )
    upcoming = Session.objects.filter(starts_at__gte=now, movie_id__in=[m.id for m in movies])
    if only_original:
        upcoming = upcoming.filter(original_language=True)
    rows = (
        upcoming.annotate(current_price=Subquery(latest_price))
        .values("movie_id")
        .annotate(min_price=Min("current_price"))
    )
    by_movie = {r["movie_id"]: r["min_price"] for r in rows}
    orig_ids = set(
        Session.objects.filter(
            starts_at__gte=now,
            original_language=True,
            movie_id__in=[m.id for m in movies],
        ).values_list("movie_id", flat=True)
    )
    for movie in movies:
        movie.min_price = by_movie.get(movie.id)
        movie.has_original = movie.id in orig_ids
        movie.poster_color = POSTER_COLORS[movie.id % len(POSTER_COLORS)]
    return movies


def movie_list(request):
    """Афиша: фильмы с предстоящими сеансами, фильтры по названию и «в оригинале»."""
    now = timezone.now()
    q = request.GET.get("q", "").strip()
    only_original = request.GET.get("original") == "1"
    show_special = request.GET.get("special") == "1"

    movies = Movie.objects.filter(sessions__starts_at__gte=now)
    if not show_special:
        movies = movies.filter(is_special=False)
    if only_original:
        movies = movies.filter(sessions__original_language=True)
    if q:
        movies = movies.filter(title__icontains=q)
    movies = _attach_min_prices(list(movies.distinct()), now, only_original)

    template = (
        "catalog/_movie_table.html"
        if request.headers.get("HX-Request")
        else "catalog/movie_list.html"
    )
    return render(
        request,
        template,
        {
            "movies": movies,
            "q": q,
            "only_original": only_original,
            "show_special": show_special,
        },
    )


def new_releases(request):
    """Новинки: фильмы с предстоящими сеансами, самые свежие по году — сверху."""
    now = timezone.now()
    movies = list(
        Movie.objects.filter(sessions__starts_at__gte=now, is_special=False)
        .distinct()
        .order_by("-year", "title")
    )
    movies = _attach_min_prices(movies, now)
    return render(request, "catalog/new_releases.html", {"movies": movies})


def _price_history_by_cinema(movie):
    """История цен фильма, сгруппированная по кинотеатрам: дневной минимум в каждом.

    Возвращает {labels: [дни], series: [{cinema, color, data: [цены по дням]}]} —
    каждая линия графика = один кинотеатр, нижняя линия = где дешевле.
    """
    rows = (
        PriceSnapshot.objects.filter(session__movie=movie)
        .values_list("session__cinema__name", "collected_at", "price_min")
        .order_by("collected_at")
    )
    by_cinema = defaultdict(dict)
    days = set()
    for cinema_name, collected_at, price in rows:
        day = timezone.localtime(collected_at).date()
        days.add(day)
        value = float(price)
        current = by_cinema[cinema_name].get(day)
        if current is None or value < current:
            by_cinema[cinema_name][day] = value
    days = sorted(days)
    series = [
        {
            "cinema": cinema_name,
            "color": CHART_COLORS[i % len(CHART_COLORS)],
            "data": [day_prices.get(day) for day in days],
        }
        for i, (cinema_name, day_prices) in enumerate(sorted(by_cinema.items()))
    ]
    return {"labels": [day.strftime("%d.%m") for day in days], "series": series}


def movie_detail(request, pk):
    """Фильм: сравнение кинотеатров по сеансам + история цен по кинотеатрам."""
    movie = get_object_or_404(Movie, pk=pk)
    upcoming = (
        movie.sessions.filter(starts_at__gte=timezone.now())
        .select_related("cinema")
        .prefetch_related("prices")
        .order_by("starts_at")
    )
    return render(
        request,
        "catalog/movie_detail.html",
        {
            "movie": movie,
            "upcoming": upcoming,
            "chart": _price_history_by_cinema(movie),
            "trend": price_trend(movie),
        },
    )
