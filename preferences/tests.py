from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class PreferenceAccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="StrongPass123!")

    def test_preferences_requires_login(self):
        response = self.client.get(reverse("preferences:settings"))
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={reverse('preferences:settings')}")

    def test_preferences_update(self):
        self.client.login(username="alice", password="StrongPass123!")
        response = self.client.post(
            reverse("preferences:settings"),
            {
                "interest-topic_terms": "remote sensing\nprecision agriculture",
                "interest-keywords": "GeoAI",
                "interest-journals_of_interest": "NATURE FOOD",
                "interest-extra_queries": "group|OG=(\"Example\")",
                "interest-arxiv_enabled": "on",
                "interest-arxiv_queries": "Crop|all:crop",
                "interest-arxiv_categories": "cs.LG",
                "preference-year_from": "2025",
                "preference-year_to": "2026",
                "preference-sort_by": "cited",
                "preference-default_result_limit": "25",
                "preference-preferred_publisher": "Nature",
                "preference-preferred_journal": "NATURE FOOD",
            },
        )
        self.assertRedirects(response, reverse("preferences:settings"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.interests.topic_terms, ["remote sensing", "precision agriculture"])
        self.assertEqual(self.user.search_preferences.sort_by, "cited")
