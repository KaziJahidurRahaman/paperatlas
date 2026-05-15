import datetime
import json
import os
import re
import time
import xml.etree.ElementTree as ET

import requests
import yaml
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from papers.models import Paper, UserPaperMatch
from papers.services.publishers import load_publishers, publisher_for

WOS_BASE_URL = "https://api.clarivate.com/apis/wos-starter/v1"
WOS_PAGE_LIMIT = 50
ARXIV_BASE_URL = "http://export.arxiv.org/api/query"
ARXIV_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
}
ARXIV_PAGE_LIMIT = 100
ARXIV_REQUEST_GAP = 3.0
ARXIV_USER_AGENT = "paperatlas/2.0 (+https://github.com/KaziJahidurRahaman/paperatlas)"
DEFAULT_RESULTS_PER_QUERY = 50


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


def load_default_query_config(path=None):
    config_path = path or settings.PAPERATLAS_QUERY_CONFIG
    with open(config_path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_publications_json(path=None):
    json_path = path or settings.PAPERATLAS_PUBLICATIONS_JSON
    with open(json_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def quote_term(term: str) -> str:
    if any(op in term for op in [" AND ", " OR ", " NOT ", "="]):
        return f"({term})"
    if term.startswith('"') and term.endswith('"'):
        return term
    return f'"{term}"'


def journal_clause(journals: list) -> str:
    if not journals:
        return ""
    return f"SO=({' OR '.join(f'\"{journal}\"' for journal in journals)})"


def resolve_year_range(year_from=None, year_to=None):
    now_year = utc_now().year
    if year_from == "CURRENT_YEAR":
        year_from = now_year
    if year_to == "CURRENT_YEAR":
        year_to = now_year
    try:
        year_from = int(year_from) if year_from is not None else None
    except (TypeError, ValueError):
        year_from = None
    try:
        year_to = int(year_to) if year_to is not None else None
    except (TypeError, ValueError):
        year_to = None
    return year_from, year_to


def apply_year(query: str, year_from=None, year_to=None) -> str:
    yf, yt = resolve_year_range(year_from, year_to)
    now_year = utc_now().year
    if yf and yt:
        return f"{query} AND PY=({yf}-{yt})"
    if yf:
        return f"{query} AND PY=({yf}-{now_year})"
    return query


def parse_citations(hit: dict) -> int:
    citations = hit.get("citations") or []
    if not citations:
        return 0
    wos = next((item for item in citations if isinstance(item, dict) and str(item.get("db", "")).upper() == "WOS"), None)
    if wos and isinstance(wos.get("count"), (int, float)):
        return int(wos["count"])
    return max(int(item.get("count", 0) or 0) for item in citations if isinstance(item, dict))


def parse_wos_record(hit: dict) -> dict:
    names = hit.get("names", {}) or {}
    authors = []
    for author in names.get("authors", []) or []:
        display = author.get("displayName") or f"{author.get('lastName', '')}, {author.get('firstName', '')}".strip(", ")
        authors.append(display)
    source = hit.get("source", {}) or {}
    pages = source.get("pages") or {}
    page_range = pages.get("range", "") if isinstance(pages, dict) else str(pages)
    if not page_range and source.get("articleNumber"):
        page_range = f"Art. {source['articleNumber']}"
    identifiers = hit.get("identifiers") or []
    doi = ""
    if isinstance(identifiers, list):
        for identifier in identifiers:
            if isinstance(identifier, dict) and identifier.get("type") == "doi":
                doi = identifier.get("value", "")
                break
    elif isinstance(identifiers, dict):
        doi = identifiers.get("doi", "") or ""
    keywords = (hit.get("keywords") or {}).get("authorKeywords") or []
    return {
        "uid": hit.get("uid", ""),
        "title": (hit.get("title") or "No title").strip(),
        "authors": authors,
        "journal": source.get("sourceTitle", "") or "",
        "year": source.get("publishYear", "") or "",
        "volume": source.get("volume", "") or "",
        "issue": source.get("issue", "") or "",
        "pages": page_range,
        "doi": doi,
        "abstract": hit.get("abstract", "") or "",
        "keywords": keywords,
        "citations": parse_citations(hit),
        "open_access": bool(((hit.get("openAccess") or {}).get("isOa", False))),
        "sources": [],
        "matched_queries": [],
    }


def build_arxiv_query(raw: str, categories: list) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    if categories:
        cat_clause = " OR ".join(f"cat:{category}" for category in categories if category)
        if cat_clause:
            return f"({raw}) AND ({cat_clause})"
    return raw


def fetch_wos_query(query: str, headers: dict, requests_per_second: float, retries: int, backoff: int, max_results: int) -> list:
    if not query or max_results <= 0:
        return []
    output = []
    page = 1
    while len(output) < max_results:
        page_size = min(WOS_PAGE_LIMIT, max_results - len(output))
        params = {"q": query, "limit": page_size, "page": page, "sortField": "PY+D"}
        response = None
        for attempt in range(retries):
            try:
                response = requests.get(f"{WOS_BASE_URL}/documents", headers=headers, params=params, timeout=30)
                response.raise_for_status()
                break
            except requests.RequestException:
                if attempt == retries - 1:
                    return output
                time.sleep(backoff)
        if response is None:
            return output
        data = response.json()
        hits = data.get("hits", []) or []
        output.extend(hits)
        total = (data.get("metadata") or {}).get("total", 0)
        if not hits or len(output) >= total:
            break
        page += 1
        time.sleep(max(1.0 / max(float(requests_per_second), 0.1), 0.5))
    return output[:max_results]


def fetch_arxiv_query(query: str, max_results: int, retries: int, backoff: int) -> list:
    if not query or max_results <= 0:
        return []
    params = {
        "search_query": query,
        "start": 0,
        "max_results": min(max_results, ARXIV_PAGE_LIMIT),
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    response = None
    for attempt in range(retries):
        try:
            response = requests.get(
                ARXIV_BASE_URL,
                params=params,
                headers={"User-Agent": ARXIV_USER_AGENT, "Accept": "application/atom+xml"},
                timeout=30,
            )
            response.raise_for_status()
            break
        except requests.RequestException:
            if attempt == retries - 1:
                return []
            time.sleep(backoff)
    if response is None:
        return []
    root = ET.fromstring(response.content)
    return root.findall("atom:entry", ARXIV_NS)


def parse_arxiv_record(entry, max_age_days=None, year_from=None, year_to=None):
    def text_of(tag):
        element = entry.find(tag, ARXIV_NS)
        return (element.text or "").strip() if element is not None and element.text else ""

    arxiv_url = text_of("atom:id")
    arxiv_id_full = arxiv_url.rsplit("/", 1)[-1]
    arxiv_id = re.sub(r"v\d+$", "", arxiv_id_full) or arxiv_id_full
    if not arxiv_id:
        return None
    published = text_of("atom:published")
    year = published[:4] if len(published) >= 4 and published[:4].isdigit() else ""
    if year:
        y = int(year)
        if year_from is not None and y < int(year_from):
            return None
        if year_to is not None and y > int(year_to):
            return None
    if max_age_days is not None and published:
        published_at = datetime.datetime.fromisoformat(published.replace("Z", "+00:00"))
        if (utc_now() - published_at).days > int(max_age_days):
            return None
    authors = []
    for author in entry.findall("atom:author", ARXIV_NS):
        name = author.find("atom:name", ARXIV_NS)
        if name is not None and name.text:
            authors.append(name.text.strip())
    categories = [item.attrib.get("term", "") for item in entry.findall("atom:category", ARXIV_NS)]
    doi_element = entry.find("arxiv:doi", ARXIV_NS)
    doi = doi_element.text.strip() if doi_element is not None and doi_element.text else f"10.48550/arXiv.{arxiv_id}"
    return {
        "uid": f"arxiv:{arxiv_id}",
        "title": " ".join(text_of("atom:title").split()) or "No title",
        "authors": authors,
        "journal": "arXiv",
        "year": year,
        "volume": "",
        "issue": "",
        "pages": f"arXiv:{arxiv_id}",
        "doi": doi,
        "abstract": "",
        "keywords": [item for item in categories if item],
        "citations": 0,
        "open_access": True,
        "sources": [],
        "matched_queries": [],
    }


def merge_records(records: list, source_label: str, query_label: str, accumulator=None):
    accumulator = accumulator or {}
    added = 0
    for record in records:
        if record is None:
            continue
        key = record.get("doi") or record.get("uid")
        if not key:
            continue
        if key in accumulator:
            existing = accumulator[key]
            if source_label not in existing["sources"]:
                existing["sources"].append(source_label)
            if query_label not in existing["matched_queries"]:
                existing["matched_queries"].append(query_label)
            continue
        record["sources"].append(source_label)
        record["matched_queries"].append(query_label)
        accumulator[key] = record
        added += 1
    return accumulator, added


def build_runtime_config(user):
    interests = user.interests
    preferences = user.search_preferences
    return {
        "topic_terms": interests.topic_terms,
        "keywords": interests.keywords,
        "journals_of_interest": interests.journals_of_interest,
        "extra_queries": interests.extra_queries,
        "arxiv_enabled": interests.arxiv_enabled,
        "arxiv_queries": interests.arxiv_queries,
        "arxiv_categories": interests.arxiv_categories,
        "year_from": preferences.year_from,
        "year_to": preferences.year_to,
        "results_per_query": preferences.default_result_limit or DEFAULT_RESULTS_PER_QUERY,
        "requests_per_second": 2,
        "retry_attempts": 3,
        "retry_backoff_seconds": 5,
    }


def build_query_plan(runtime_config):
    journals = runtime_config.get("journals_of_interest") or []
    scope = journal_clause(journals)
    year_from = runtime_config.get("year_from")
    year_to = runtime_config.get("year_to")
    topic_queries = [
        {"label": term, "query": apply_year(f"TS=({quote_term(term)}) AND {scope}", year_from, year_to)}
        for term in runtime_config.get("topic_terms") or []
        if scope
    ]
    keyword_queries = [
        {"label": keyword, "query": apply_year(f"TS=({quote_term(keyword)}) AND {scope}", year_from, year_to)}
        for keyword in runtime_config.get("keywords") or []
        if scope
    ]
    journal_queries = [{"label": journal, "query": f'SO=("{journal}")'} for journal in journals]
    extra_queries = []
    for item in runtime_config.get("extra_queries") or []:
        raw = (item or {}).get("query", "")
        label = (item or {}).get("label", raw)
        if not raw:
            continue
        query = f"({raw}) AND {scope}" if scope else raw
        extra_queries.append({"label": label, "query": query})
    arxiv_queries = []
    if runtime_config.get("arxiv_enabled"):
        for item in runtime_config.get("arxiv_queries") or []:
            raw = (item or {}).get("query", "")
            label = (item or {}).get("label", raw)
            query = build_arxiv_query(raw, runtime_config.get("arxiv_categories") or [])
            if query:
                arxiv_queries.append({"label": label, "query": query})
    return {
        "topic": topic_queries,
        "keyword": keyword_queries,
        "journal": journal_queries,
        "extra": extra_queries,
        "arxiv": arxiv_queries,
    }


def upsert_paper(record, publisher_groups, publisher_overrides):
    canonical_key = record.get("doi") or record.get("uid")
    paper, _ = Paper.objects.update_or_create(
        canonical_key=canonical_key,
        defaults={
            "uid": record.get("uid", ""),
            "doi": record.get("doi", ""),
            "title": record.get("title", ""),
            "authors": record.get("authors", []),
            "journal": record.get("journal", ""),
            "publisher": publisher_for(record.get("journal", ""), publisher_groups, publisher_overrides),
            "year": str(record.get("year", "") or ""),
            "volume": record.get("volume", ""),
            "issue": record.get("issue", ""),
            "pages": record.get("pages", ""),
            "abstract": record.get("abstract", ""),
            "keywords": record.get("keywords", []),
            "citations": int(record.get("citations", 0) or 0),
            "open_access": bool(record.get("open_access", False)),
            "sources": record.get("sources", []),
        },
    )
    return paper


def import_publications_dataset(payload):
    publisher_groups, publisher_overrides = load_publishers()
    count = 0
    for record in payload.get("publications") or []:
        upsert_paper(record, publisher_groups, publisher_overrides)
        count += 1
    return count


def import_publications_file(path=None):
    payload = load_publications_json(path)
    return import_publications_dataset(payload)


def fetch_records_for_user(user):
    runtime_config = build_runtime_config(user)
    plan = build_query_plan(runtime_config)
    headers = {"X-ApiKey": settings.WOS_API_KEY, "Accept": "application/json"} if settings.WOS_API_KEY else {}
    records = {}
    per_query = int(runtime_config.get("results_per_query") or DEFAULT_RESULTS_PER_QUERY)
    retries = int(runtime_config.get("retry_attempts") or 3)
    backoff = int(runtime_config.get("retry_backoff_seconds") or 5)
    requests_per_second = float(runtime_config.get("requests_per_second") or 2)
    year_from, year_to = resolve_year_range(runtime_config.get("year_from"), runtime_config.get("year_to"))

    if headers and (plan["topic"] or plan["keyword"] or plan["journal"] or plan["extra"]):
        for label_kind in ("topic", "keyword", "journal", "extra"):
            for item in plan[label_kind]:
                hits = fetch_wos_query(item["query"], headers, requests_per_second, retries, backoff, per_query)
                parsed = [parse_wos_record(hit) for hit in hits]
                records, _ = merge_records(parsed, label_kind, f"{label_kind}:{item['label']}", records)
    for index, item in enumerate(plan["arxiv"]):
        entries = fetch_arxiv_query(item["query"], per_query, retries, backoff)
        parsed = [parse_arxiv_record(entry, max_age_days=365, year_from=year_from, year_to=year_to) for entry in entries]
        records, _ = merge_records(parsed, "arxiv", f"arxiv:{item['label']}", records)
        if index < len(plan["arxiv"]) - 1:
            time.sleep(ARXIV_REQUEST_GAP)
    return list(records.values())


def refresh_user_feed(user):
    publisher_groups, publisher_overrides = load_publishers()
    fetched_records = fetch_records_for_user(user)
    with transaction.atomic():
        user.paper_matches.all().delete()
        for record in fetched_records:
            paper = upsert_paper(record, publisher_groups, publisher_overrides)
            UserPaperMatch.objects.create(
                user=user,
                paper=paper,
                matched_queries=record.get("matched_queries", []),
                sources=record.get("sources", []),
                relevance_score=float(len(record.get("matched_queries", []))),
                last_matched_at=timezone.now(),
            )
        profile = user.profile
        profile.last_refreshed_at = timezone.now()
        profile.save(update_fields=["last_refreshed_at"])
    return len(fetched_records)
