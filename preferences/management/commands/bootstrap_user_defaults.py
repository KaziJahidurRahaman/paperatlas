from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from papers.services.fetch_engine import load_default_query_config

User = get_user_model()


class Command(BaseCommand):
    help = "Bootstrap a user's interests and preferences from query_config.yml"

    def add_arguments(self, parser):
        parser.add_argument("username")

    def handle(self, *args, **options):
        username = options["username"]
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist as exc:
            raise CommandError(f"User '{username}' does not exist.") from exc

        config = load_default_query_config()
        topic_query = config.get("topic_query") or {}
        arxiv = config.get("arxiv") or {}

        interests = user.interests
        interests.topic_terms = topic_query.get("terms") or []
        interests.keywords = config.get("keywords") or []
        interests.journals_of_interest = config.get("journals_of_interest") or []
        interests.extra_queries = config.get("extra_queries") or []
        interests.arxiv_enabled = bool(arxiv.get("enabled", True))
        interests.arxiv_queries = arxiv.get("queries") or []
        interests.arxiv_categories = arxiv.get("categories") or []
        interests.save()

        prefs = user.search_preferences
        prefs.year_from = topic_query.get("year_from") if isinstance(topic_query.get("year_from"), int) else None
        prefs.year_to = topic_query.get("year_to") if isinstance(topic_query.get("year_to"), int) else None
        prefs.default_result_limit = int((config.get("fetch") or {}).get("results_per_query", 50) or 50)
        prefs.save()

        self.stdout.write(self.style.SUCCESS(f"Bootstrapped defaults for {username}."))
