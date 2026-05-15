from django.contrib import admin

from papers.models import FavoritePaper, Paper, UserPaperMatch


@admin.register(Paper)
class PaperAdmin(admin.ModelAdmin):
    list_display = ("title", "journal", "publisher", "year", "citations")
    search_fields = ("title", "doi", "uid", "journal", "publisher")
    list_filter = ("publisher", "year", "open_access")


@admin.register(UserPaperMatch)
class UserPaperMatchAdmin(admin.ModelAdmin):
    list_display = ("user", "paper", "relevance_score", "last_matched_at")
    search_fields = ("user__username", "paper__title")


@admin.register(FavoritePaper)
class FavoritePaperAdmin(admin.ModelAdmin):
    list_display = ("user", "paper", "created_at")
    search_fields = ("user__username", "paper__title")
