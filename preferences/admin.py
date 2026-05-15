from django.contrib import admin

from preferences.models import SearchPreference, UserInterest


@admin.register(UserInterest)
class UserInterestAdmin(admin.ModelAdmin):
    list_display = ("user", "arxiv_enabled", "updated_at")
    search_fields = ("user__username",)


@admin.register(SearchPreference)
class SearchPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "sort_by", "default_result_limit", "updated_at")
    search_fields = ("user__username",)
