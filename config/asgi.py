"""
asgi.py — ASGI entry point.
============================
Ready for async if needed in future (WebSockets, async views).
Currently not used — gunicorn uses wsgi.py.

To switch to async serving:
    uvicorn config.asgi:application --workers 2
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

application = get_asgi_application()