from django.contrib import admin

from .models import ScrapeRun


@admin.register(ScrapeRun)
class ScrapeRunAdmin(admin.ModelAdmin):
    list_display = ["source", "status", "started_at", "finished_at", "sessions_found"]
    list_filter = ["source", "status"]
    readonly_fields = ["source", "status", "started_at", "finished_at", "sessions_found", "error"]
