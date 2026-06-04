"""
urls.py — Root URL configuration.
==================================
Delegates routing to each app's urls.py.
No business logic here — this file is a router only.

URL structure:
    /                   → apps.landing      (homepage)
    /auth/              → apps.accounts     (login, register, profile)
    /accounts/          → allauth           (Google OAuth callback etc.)
    /convert/           → apps.conversions  (upload, result, download)
    /dashboard/         → apps.dashboard    (history, quota — v2)
    /billing/           → apps.billing      (plans, payments — v2)
    /admin/             → Django admin (Jazzmin)
    /health/            → HealthCheckView   (Render + Uptime Robot ping)
"""

from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


# ─── Health check ─────────────────────────────────────────────────────────────
def health_check(request):
    """
    Lightweight endpoint for Uptime Robot + Render health checks.
    Returns 200 JSON. No DB query — pure response.
    Telegram bot also pings this every 14 minutes to keep Render alive.
    """
    return JsonResponse({"status": "ok"})


# ─── URL patterns ─────────────────────────────────────────────────────────────
urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),

    # Health check (no auth required)
    path("health/", health_check, name="health_check"),

    # Landing page
    path("", include("apps.landing.urls", namespace="landing")),

    # Authentication (custom views)
    path("auth/", include("apps.accounts.urls", namespace="accounts")),

    # Google OAuth + allauth internals
    path("accounts/", include("allauth.urls")),

    # Core feature — conversion
    path("convert/", include("apps.conversions.urls", namespace="conversions")),

    # Dashboard — v2
    path("dashboard/", include("apps.dashboard.urls", namespace="dashboard")),

    # Billing — v2
    path("billing/", include("apps.billing.urls", namespace="billing")),
]