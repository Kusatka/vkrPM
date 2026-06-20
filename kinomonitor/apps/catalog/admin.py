from django.contrib import admin

from .models import Cinema, Movie, PriceSnapshot, Session


@admin.register(Cinema)
class CinemaAdmin(admin.ModelAdmin):
    list_display = ["name", "network", "is_niche", "is_monitored", "afisha_slug"]
    list_filter = ["network", "is_niche", "is_monitored"]
    list_editable = ["is_monitored"]
    search_fields = ["name", "afisha_slug"]
    prepopulated_fields = {"slug": ["name"]}


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ["title", "original_title", "year", "is_special"]
    list_filter = ["is_special"]
    list_editable = ["is_special"]
    search_fields = ["title", "original_title"]


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ["movie", "cinema", "starts_at", "format", "original_language", "source"]
    list_filter = ["source", "cinema", "format", "original_language"]
    date_hierarchy = "starts_at"


@admin.register(PriceSnapshot)
class PriceSnapshotAdmin(admin.ModelAdmin):
    list_display = ["session", "price_min", "price_max", "collected_at"]
    date_hierarchy = "collected_at"
