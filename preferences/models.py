from django.conf import settings
from django.db import models


class UserInterest(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="interests")
    topic_terms = models.JSONField(default=list, blank=True)
    keywords = models.JSONField(default=list, blank=True)
    journals_of_interest = models.JSONField(default=list, blank=True)
    extra_queries = models.JSONField(default=list, blank=True)
    arxiv_enabled = models.BooleanField(default=True)
    arxiv_queries = models.JSONField(default=list, blank=True)
    arxiv_categories = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Interests for {self.user.get_username()}"


class SearchPreference(models.Model):
    SORT_CHOICES = [
        ("year", "Newest first"),
        ("cited", "Most cited"),
        ("alpha", "A → Z"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="search_preferences")
    year_from = models.PositiveIntegerField(null=True, blank=True)
    year_to = models.PositiveIntegerField(null=True, blank=True)
    sort_by = models.CharField(max_length=20, choices=SORT_CHOICES, default="year")
    default_result_limit = models.PositiveIntegerField(default=50)
    preferred_publisher = models.CharField(max_length=120, blank=True)
    preferred_journal = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Search preferences for {self.user.get_username()}"
