from django.urls import path

from dashboard.views import dashboard_view, saved_papers_view, toggle_favorite_view

app_name = "dashboard"

urlpatterns = [
    path("", dashboard_view, name="home"),
    path("saved/", saved_papers_view, name="saved"),
    path("papers/<int:paper_id>/favorite/", toggle_favorite_view, name="toggle_favorite"),
]
