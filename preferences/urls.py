from django.urls import path

from preferences.views import preferences_view, refresh_feed_view

app_name = "preferences"

urlpatterns = [
    path("", preferences_view, name="settings"),
    path("refresh/", refresh_feed_view, name="refresh"),
]
