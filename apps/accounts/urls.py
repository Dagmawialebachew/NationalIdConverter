"""
apps/accounts/urls.py
=====================
URL configuration for the accounts app.

Included in config/urls.py under the 'auth/' prefix:
    path("auth/", include("apps.accounts.urls", namespace="accounts")),

Resulting URLs:
    /auth/register/          → RegisterView
    /auth/login/             → LoginView
    /auth/logout/            → LogoutView
    /auth/profile/           → ProfileView
    /auth/change-password/   → ChangePasswordView
"""

from django.urls import path

from apps.accounts import views

app_name = "accounts"

urlpatterns = [
    path("register/",        views.RegisterView.as_view(),       name="register"),
    path("login/",           views.LoginView.as_view(),          name="login"),
    path("logout/",          views.LogoutView.as_view(),         name="logout"),
    path("profile/",         views.ProfileView.as_view(),        name="profile"),
    path("change-password/", views.ChangePasswordView.as_view(), name="change_password"),
]