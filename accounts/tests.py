from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class AccountTests(TestCase):
    def test_register_creates_related_profile_and_preferences(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "alice",
                "email": "alice@example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )
        self.assertRedirects(response, reverse("dashboard:home"))
        user = User.objects.get(username="alice")
        self.assertEqual(user.email, "alice@example.com")
        self.assertTrue(hasattr(user, "profile"))
        self.assertTrue(hasattr(user, "interests"))
        self.assertTrue(hasattr(user, "search_preferences"))
