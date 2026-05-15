from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from papers.services.fetch_engine import refresh_user_feed

User = get_user_model()


class Command(BaseCommand):
    help = "Refresh one user's feed or all users' feeds"

    def add_arguments(self, parser):
        parser.add_argument("--username", default=None)

    def handle(self, *args, **options):
        username = options["username"]
        if username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist as exc:
                raise CommandError(f"User '{username}' does not exist.") from exc
            count = refresh_user_feed(user)
            self.stdout.write(self.style.SUCCESS(f"Refreshed {username}: {count} papers."))
            return
        for user in User.objects.all():
            count = refresh_user_feed(user)
            self.stdout.write(self.style.SUCCESS(f"Refreshed {user.username}: {count} papers."))
