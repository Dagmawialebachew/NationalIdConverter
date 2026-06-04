"""
wsgi.py — WSGI entry point.
============================
Used by gunicorn on Render:
    gunicorn config.wsgi:application --workers 2

Workers = 2 is safe for Render free tier (512MB RAM).
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

application = get_wsgi_application()