from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import UserProfile
from preferences.models import SearchPreference, UserInterest

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_related_records(sender, instance, created, **kwargs):
    if not created:
        return
    UserProfile.objects.create(user=instance, display_name=instance.get_username())
    UserInterest.objects.create(user=instance)
    SearchPreference.objects.create(user=instance)
