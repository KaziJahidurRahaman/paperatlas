from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from papers.models import Paper
from papers.services.fetch_engine import build_query_plan, import_publications_file, merge_records

User = get_user_model()


class FetchEngineTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="StrongPass123!")
        self.user.interests.topic_terms = ["remote sensing"]
        self.user.interests.keywords = ["GeoAI"]
        self.user.interests.journals_of_interest = ["NATURE FOOD"]
        self.user.interests.extra_queries = [{"label": "Org", "query": 'OG=("Example")'}]
        self.user.interests.arxiv_queries = [{"label": "Crop", "query": 'all:"crop model"'}]
        self.user.interests.arxiv_categories = ["cs.LG"]
        self.user.interests.save()
        self.user.search_preferences.year_from = 2025
        self.user.search_preferences.year_to = 2026
        self.user.search_preferences.save()

    def test_build_query_plan_uses_user_interests(self):
        plan = build_query_plan({
            "topic_terms": self.user.interests.topic_terms,
            "keywords": self.user.interests.keywords,
            "journals_of_interest": self.user.interests.journals_of_interest,
            "extra_queries": self.user.interests.extra_queries,
            "arxiv_enabled": True,
            "arxiv_queries": self.user.interests.arxiv_queries,
            "arxiv_categories": self.user.interests.arxiv_categories,
            "year_from": self.user.search_preferences.year_from,
            "year_to": self.user.search_preferences.year_to,
        })
        self.assertIn('TS=("remote sensing") AND SO=("NATURE FOOD") AND PY=(2025-2026)', [item["query"] for item in plan["topic"]])
        self.assertEqual(plan["arxiv"][0]["query"], '(all:"crop model") AND (cat:cs.LG)')

    def test_merge_records_deduplicates_by_doi(self):
        records, added = merge_records([
            {"doi": "10.1/test", "uid": "", "sources": [], "matched_queries": []},
            {"doi": "10.1/test", "uid": "uid-2", "sources": [], "matched_queries": []},
        ], "topic", "topic:test")
        self.assertEqual(added, 1)
        self.assertEqual(len(records), 1)

    def test_import_publications_file_creates_papers(self):
        with TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "publications.json"
            path.write_text(
                '{"publications": [{"uid": "uid-1", "doi": "10.1/example", "title": "Imported", "authors": ["A"], "journal": "NATURE FOOD", "year": "2026", "volume": "1", "issue": "1", "pages": "1-2", "abstract": "", "keywords": ["x"], "citations": 3, "open_access": true, "sources": ["topic"]}]}',
                encoding="utf-8",
            )
            count = import_publications_file(path)
        self.assertEqual(count, 1)
        self.assertTrue(Paper.objects.filter(canonical_key="10.1/example", publisher="Nature").exists())
