"""
apps/conversions/apps.py
========================
AppConfig for the conversions app.

Imports signals in ready() so they're registered at startup.

Add to INSTALLED_APPS in settings:
    "apps.conversions.apps.ConversionsConfig",
    # or just:
    "apps.conversions",
"""

from django.apps import AppConfig


class ConversionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name               = "apps.conversions"
    verbose_name       = "Conversions"

    def ready(self):
        import apps.conversions.signals  # noqa: F401 — registers signal handlers