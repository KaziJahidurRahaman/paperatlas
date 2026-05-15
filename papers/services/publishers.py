import re

from django.conf import settings

import yaml


def load_publishers(path=None):
    config_path = path or settings.PAPERATLAS_PUBLISHERS_CONFIG
    with open(config_path, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    groups = []
    for entry in data.get("publishers") or []:
        label = (entry.get("label") or "").strip()
        patterns = entry.get("patterns") or []
        if not label or not patterns:
            continue
        groups.append({"label": label, "patterns": [re.compile(pattern, re.IGNORECASE) for pattern in patterns]})
    overrides = {str(key).lower(): value for key, value in (data.get("overrides") or {}).items()}
    return groups, overrides


def publisher_for(journal, groups=None, overrides=None):
    journal_name = str(journal or "").strip()
    if not journal_name:
        return "Other"
    groups = groups if groups is not None else load_publishers()[0]
    overrides = overrides if overrides is not None else load_publishers()[1]
    override = overrides.get(journal_name.lower())
    if override:
        return override
    for group in groups:
        if any(pattern.search(journal_name) for pattern in group["patterns"]):
            return group["label"]
    return "Other"
