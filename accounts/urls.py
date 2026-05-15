from django.contrib.auth import views as auth_views
from django.urls import path

from accounts.views import profile_view, register_view

app_name = "accounts"

urlpatterns = [
    path("register/", register_view, name="register"),
    path("profile/", profile_view, name="profile"),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(template_name="registration/logged_out.html"), name="logout"),
]
