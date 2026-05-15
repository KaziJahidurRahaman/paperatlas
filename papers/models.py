from django.conf import settings
from django.db import models
from django.utils import timezone


class Paper(models.Model):
    canonical_key = models.CharField(max_length=255, unique=True)
    uid = models.CharField(max_length=255, blank=True, db_index=True)
    doi = models.CharField(max_length=255, blank=True, db_index=True)
    title = models.TextField()
    authors = models.JSONField(default=list, blank=True)
    journal = models.CharField(max_length=255, blank=True, db_index=True)
    publisher = models.CharField(max_length=120, blank=True, db_index=True)
    year = models.CharField(max_length=10, blank=True, db_index=True)
    volume = models.CharField(max_length=50, blank=True)
    issue = models.CharField(max_length=50, blank=True)
    pages = models.CharField(max_length=100, blank=True)
    abstract = models.TextField(blank=True)
    keywords = models.JSONField(default=list, blank=True)
    citations = models.PositiveIntegerField(default=0)
    open_access = models.BooleanField(default=False)
    sources = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-year", "-citations", "title")

    def __str__(self):
        return self.title


class UserPaperMatch(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="paper_matches")
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name="user_matches")
    matched_queries = models.JSONField(default=list, blank=True)
    sources = models.JSONField(default=list, blank=True)
    relevance_score = models.FloatField(default=0)
    last_matched_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("user", "paper")
        ordering = ("-last_matched_at", "-relevance_score")

    def __str__(self):
        return f"{self.user} ↔ {self.paper}"


class FavoritePaper(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorite_papers")
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "paper")
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.user} saved {self.paper}"
