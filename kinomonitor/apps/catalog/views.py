from django.db.models import Min
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .analytics import price_trend
from .models import Movie, PriceSnapshot


def movie_list(request):
    """Афиша: фильмы с предстоящими сеансами, фильтры по названию и «в оригинале»."""
    q = request.GET.get("q", "").strip()
    only_original = request.GET.get("original") == "1"
    show_special = request.GET.get("special") == "1"

    movies = Movie.objects.filter(sessions__starts_at__gte=timezone.now())
    if not show_special:
        movies = movies.filter(is_special=False)
    if only_original:
        movies = movies.filter(sessions__original_language=True)
    if q:
        movies = movies.filter(title__icontains=q)
    movies = movies.distinct().annotate(min_price=Min("sessions__prices__price_min"))

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
