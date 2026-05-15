from django.contrib import admin

from accounts.models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "affiliation", "last_refreshed_at")
    search_fields = ("user__username", "display_name", "affiliation")
