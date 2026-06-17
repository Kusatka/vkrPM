from django.contrib import admin

from .models import NotificationLog


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ["user", "session", "sent_at"]
    readonly_fields = ["user", "subscription", "session", "text", "sent_at"]
