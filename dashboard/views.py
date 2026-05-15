from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from papers.models import FavoritePaper, Paper, UserPaperMatch


def _filter_matches(request):
    user = request.user
    query = request.GET.get("q", "").strip().lower()
    journal = request.GET.get("journal", "").strip()
    publisher = request.GET.get("publisher", "").strip()
    year = request.GET.get("year", "").strip()
    sort_by = request.GET.get("sort", user.search_preferences.sort_by)

    matches = (
        UserPaperMatch.objects.filter(user=user)
        .select_related("paper")
        .order_by("-last_matched_at")
    )
    if journal:
        matches = matches.filter(paper__journal=journal)
    if publisher:
        matches = matches.filter(paper__publisher=publisher)
    if year:
        matches = matches.filter(paper__year=str(year))
    if query:
        matches = matches.filter(
            Q(paper__title__icontains=query)
            | Q(paper__journal__icontains=query)
            | Q(paper__doi__icontains=query)
        )

    if sort_by == "cited":
        matches = matches.order_by("-paper__citations", "-paper__year", "paper__title")
    elif sort_by == "alpha":
        matches = matches.order_by("paper__title")
    else:
        matches = matches.order_by("-paper__year", "-paper__citations", "paper__title")

    favorite_ids = set(FavoritePaper.objects.filter(user=user).values_list("paper_id", flat=True))
    items = []
    for match in matches:
        paper = match.paper
        if query:
            searchable = " ".join(
                [
                    paper.title or "",
                    paper.journal or "",
                    paper.doi or "",
                    " ".join(paper.authors or []),
                    " ".join(paper.keywords or []),
                ]
            ).lower()
            if query not in searchable:
                continue
        paper.is_favorite = paper.id in favorite_ids
        items.append(match)
    return items, {"q": query, "journal": journal, "publisher": publisher, "year": year, "sort": sort_by}


@login_required
def dashboard_view(request):
    matches, filters = _filter_matches(request)
    all_matches = UserPaperMatch.objects.filter(user=request.user).select_related("paper")
    journals = sorted({match.paper.journal for match in all_matches if match.paper.journal})
    publishers = sorted({match.paper.publisher for match in all_matches if match.paper.publisher})
    years = sorted({match.paper.year for match in all_matches if match.paper.year}, reverse=True)
    return render(
        request,
        "dashboard/dashboard.html",
        {
            "matches": matches,
            "filters": filters,
            "journals": journals,
            "publishers": publishers,
            "years": years,
        },
    )


@login_required
def saved_papers_view(request):
    favorites = FavoritePaper.objects.filter(user=request.user).select_related("paper")
    return render(request, "dashboard/saved_papers.html", {"favorites": favorites})


@login_required
def toggle_favorite_view(request, paper_id):
    paper = get_object_or_404(Paper, pk=paper_id)
    favorite, created = FavoritePaper.objects.get_or_create(user=request.user, paper=paper)
    if not created:
        favorite.delete()
        messages.success(request, "Paper removed from saved list.")
    else:
        messages.success(request, "Paper saved.")
    return redirect(request.META.get("HTTP_REFERER", "dashboard:home"))
