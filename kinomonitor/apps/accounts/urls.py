from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("subscriptions/", views.subscriptions, name="subscriptions"),
    path("subscriptions/<int:pk>/delete/", views.subscription_delete, name="subscription_delete"),
]
