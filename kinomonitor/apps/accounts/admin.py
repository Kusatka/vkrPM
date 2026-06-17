from django.contrib import admin

from .models import Subscription, TelegramProfile


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["user", "movie", "cinema", "max_price", "is_active"]
    list_filter = ["is_active"]


@admin.register(TelegramProfile)
class TelegramProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "chat_id", "linked_at"]
    readonly_fields = ["link_code"]
