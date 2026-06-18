from django.db.models import Min, OuterRef, Subquery
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .analytics import price_trend
from .models import Movie, PriceSnapshot, Session


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
    movies = list(movies.distinct())

    # «Цена от» = минимум по ПОСЛЕДНИМ снимкам будущих сеансов. Старый код брал
    # Min по всей истории снимков и показывал устаревший исторический минимум,
    # которого уже не купить. Здесь для каждого сеанса берём актуальную цену
    # (последний снимок), и только потом минимум по фильму.
    latest_price = (
        PriceSnapshot.objects.filter(session=OuterRef("pk"))
        .order_by("-collected_at")
        .values("price_min")[:1]
    )
    upcoming = Session.objects.filter(starts_at__gte=now, movie_id__in=[m.id for m in movies])
    if only_original:
        upcoming = upcoming.filter(original_language=True)
    price_rows = (
        upcoming.annotate(current_price=Subquery(latest_price))
        .values("movie_id")
        .annotate(min_price=Min("current_price"))
    )
    price_by_movie = {row["movie_id"]: row["min_price"] for row in price_rows}
    for movie in movies:
        movie.min_price = price_by_movie.get(movie.id)

    if request.headers.get("HX-Request"):
        template = "catalog/_movie_table.html"
    else:
        template = "catalog/movie_list.html"
    context = {
        "movies": movies,
        "q": q,
        "only_original": only_original,
        "show_special": show_special,
    }
    return render(request, template, context)


def movie_detail(request, pk):
    """Фильм: сравнение кинотеатров по предстоящим сеансам + график истории цен."""
    movie = get_object_or_404(Movie, pk=pk)
    upcoming = (
        movie.sessions.filter(starts_at__gte=timezone.now())
        .select_related("cinema")
        .prefetch_related("prices")
        .order_by("starts_at")
    )
    history = (
        PriceSnapshot.objects.filter(session__movie=movie)
        .order_by("collected_at")
        .values_list("collected_at", "price_min")
    )
    chart = {
        "labels": [timezone.localtime(dt).strftime("%d.%m %H:%M") for dt, _ in history],
        "values": [float(p) for _, p in history],
    }
    return render(
        request,
        "catalog/movie_detail.html",
        {"movie": movie, "upcoming": upcoming, "chart": chart, "trend": price_trend(movie)},
    )
