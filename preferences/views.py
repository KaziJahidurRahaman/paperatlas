from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from preferences.forms import SearchPreferenceForm, UserInterestForm
from papers.services.fetch_engine import refresh_user_feed


@login_required
def preferences_view(request):
    interest_form = UserInterestForm(request.POST or None, instance=request.user.interests, prefix="interest")
    preference_form = SearchPreferenceForm(
        request.POST or None,
        instance=request.user.search_preferences,
        prefix="preference",
    )
    if request.method == "POST" and interest_form.is_valid() and preference_form.is_valid():
        interest_form.save()
        preference_form.save()
        messages.success(request, "Preferences updated.")
        return redirect("preferences:settings")
    return render(
        request,
        "preferences/preferences_form.html",
        {"interest_form": interest_form, "preference_form": preference_form},
    )


@login_required
def refresh_feed_view(request):
    refresh_user_feed(request.user)
    messages.success(request, "Your paper feed has been refreshed.")
    return redirect("dashboard:home")
