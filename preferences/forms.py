from django import forms

from preferences.models import SearchPreference, UserInterest


class LineSeparatedListField(forms.CharField):
    def to_python(self, value):
        value = super().to_python(value)
        if not value:
            return []
        return [line.strip() for line in value.splitlines() if line.strip()]


class LabelQueryListField(forms.CharField):
    def to_python(self, value):
        value = super().to_python(value)
        if not value:
            return []
        rows = []
        for line in value.splitlines():
            raw = line.strip()
            if not raw:
                continue
            if "|" in raw:
                label, query = raw.split("|", 1)
            else:
                label, query = raw, raw
            rows.append({"label": label.strip(), "query": query.strip()})
        return rows


class UserInterestForm(forms.ModelForm):
    topic_terms = LineSeparatedListField(required=False, widget=forms.Textarea(attrs={"rows": 5}))
    keywords = LineSeparatedListField(required=False, widget=forms.Textarea(attrs={"rows": 5}))
    journals_of_interest = LineSeparatedListField(required=False, widget=forms.Textarea(attrs={"rows": 5}))
    arxiv_categories = LineSeparatedListField(required=False, widget=forms.Textarea(attrs={"rows": 4}))
    extra_queries = LabelQueryListField(required=False, widget=forms.Textarea(attrs={"rows": 4}))
    arxiv_queries = LabelQueryListField(required=False, widget=forms.Textarea(attrs={"rows": 5}))

    class Meta:
        model = UserInterest
        fields = (
            "topic_terms",
            "keywords",
            "journals_of_interest",
            "extra_queries",
            "arxiv_enabled",
            "arxiv_queries",
            "arxiv_categories",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial.setdefault("topic_terms", "\n".join(self.instance.topic_terms))
            self.initial.setdefault("keywords", "\n".join(self.instance.keywords))
            self.initial.setdefault("journals_of_interest", "\n".join(self.instance.journals_of_interest))
            self.initial.setdefault("arxiv_categories", "\n".join(self.instance.arxiv_categories))
            self.initial.setdefault(
                "extra_queries",
                "\n".join(f"{item.get('label', '')}|{item.get('query', '')}" for item in self.instance.extra_queries),
            )
            self.initial.setdefault(
                "arxiv_queries",
                "\n".join(f"{item.get('label', '')}|{item.get('query', '')}" for item in self.instance.arxiv_queries),
            )


class SearchPreferenceForm(forms.ModelForm):
    class Meta:
        model = SearchPreference
        fields = (
            "year_from",
            "year_to",
            "sort_by",
            "default_result_limit",
            "preferred_publisher",
            "preferred_journal",
        )
