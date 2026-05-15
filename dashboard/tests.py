from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from papers.models import FavoritePaper, Paper, UserPaperMatch

User = get_user_model()


class DashboardAccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="StrongPass123!")
        self.other_user = User.objects.create_user(username="bob", password="StrongPass123!")
        self.paper = Paper.objects.create(
            canonical_key="doi:10.1/test",
            doi="10.1/test",
            title="Test Paper",
            journal="NATURE FOOD",
            publisher="Nature",
            year="2026",
        )
        self.match = UserPaperMatch.objects.create(user=self.user, paper=self.paper, matched_queries=["topic:test"])
        FavoritePaper.objects.create(user=self.user, paper=self.paper)

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard:home"))
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={reverse('dashboard:home')}")

    def test_dashboard_shows_only_current_users_matches(self):
        self.client.login(username="alice", password="StrongPass123!")
        response = self.client.get(reverse("dashboard:home"))
        self.assertContains(response, "Test Paper")
        UserPaperMatch.objects.create(user=self.other_user, paper=self.paper, matched_queries=["topic:other"])
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(list(response.context["matches"])[0].user, self.user)

    def test_saved_papers_requires_login(self):
        response = self.client.get(reverse("dashboard:saved"))
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={reverse('dashboard:saved')}")

    def test_toggle_favorite_removes_existing_favorite(self):
        self.client.login(username="alice", password="StrongPass123!")
        response = self.client.get(reverse("dashboard:toggle_favorite", args=[self.paper.id]))
        self.assertRedirects(response, reverse("dashboard:home"))
        self.assertFalse(FavoritePaper.objects.filter(user=self.user, paper=self.paper).exists())
