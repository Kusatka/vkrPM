from django.contrib import admin
from django.urls import include, path

from apps.catalog.api import router

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    path("accounts/", include("apps.accounts.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("apps.catalog.urls")),
]
