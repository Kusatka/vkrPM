from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.movie_list, name="movie_list"),
    path("new/", views.new_releases, name="new_releases"),
    path("movie/<int:pk>/", views.movie_detail, name="movie_detail"),
]
