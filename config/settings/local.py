"""
Local development settings.
Extends base.py.
Usage: export DJANGO_SETTINGS_MODULE=config.settings.local
"""
from .base import *  # noqa
"""
local.py — Development settings.
==================================
Extends base.py. Used on your local machine only.

Activate with:
    export DJANGO_SETTINGS_MODULE=config.settings.local

Or in .env:
    DJANGO_SETTINGS_MODULE=config.settings.local
"""

from .base import *  # noqa: F401, F403

# ─── Debug ────────────────────────────────────────────────────────────────────
DEBUG         = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# ─── Database ─────────────────────────────────────────────────────────────────
# In development we still use Neon Postgres (same cloud DB, dev branch ideally)
# Override DATABASE_URL in .env for local if you want a separate dev DB
# DATABASES already set in base.py via env("DATABASE_URL")

# ─── Email (print to console in dev — no SMTP needed) ────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ─── Django Debug Toolbar (optional — install separately if needed) ───────────
# pip install django-debug-toolbar
# INSTALLED_APPS += ["debug_toolbar"]
# MIDDLEWARE    += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
# INTERNAL_IPS   = ["127.0.0.1"]

# ─── Allauth: skip email verification locally ─────────────────────────────────
ACCOUNT_EMAIL_VERIFICATION = "none"   # Don't require email verify in dev

# ─── Logging: verbose in dev ─────────────────────────────────────────────────
LOGGING["root"]["level"] = "DEBUG"  # type: ignore[index]