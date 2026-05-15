from celery import shared_task
from django.contrib.auth import get_user_model

from papers.services.fetch_engine import refresh_user_feed

User = get_user_model()


@shared_task(name="papers.tasks.refresh_all_user_feeds")
def refresh_all_user_feeds():
    for user in User.objects.all():
        refresh_user_feed(user)


@shared_task(name="papers.tasks.refresh_single_user_feed")
def refresh_single_user_feed(user_id):
    refresh_user_feed(User.objects.get(pk=user_id))
