from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from accounts.forms import ProfileForm, RegisterForm


def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard:home")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        user.email = form.cleaned_data["email"]
        user.save(update_fields=["email"])
        login(request, user)
        messages.success(request, "Welcome to PaperAtlas.")
        return redirect("dashboard:home")
    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile_view(request):
    form = ProfileForm(request.POST or None, instance=request.user.profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("accounts:profile")
    return render(request, "accounts/profile.html", {"form": form})
