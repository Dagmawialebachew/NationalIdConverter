"""
apps/accounts/apps.py
=====================
AppConfig for the accounts app.

The ready() method imports signals so they're registered when
Django starts up. Without this, signals defined in signals.py
are never connected.

Add to INSTALLED_APPS in settings:
    "apps.accounts.apps.AccountsConfig",
    # or just:
    "apps.accounts",
"""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name               = "apps.accounts"
    verbose_name       = "Accounts"

    def ready(self):
        import apps.accounts.signals  # noqa: F401 — connects signal handlers