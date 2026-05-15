from django.core.management.base import BaseCommand

from papers.services.fetch_engine import import_publications_file


class Command(BaseCommand):
    help = "Import papers from data/publications.json into the Paper model"

    def add_arguments(self, parser):
        parser.add_argument("--path", default=None)

    def handle(self, *args, **options):
        count = import_publications_file(options["path"])
        self.stdout.write(self.style.SUCCESS(f"Imported {count} papers."))
