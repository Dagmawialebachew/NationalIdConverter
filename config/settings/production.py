"""
Production settings for Render deployment.
Extends base.py.
Usage: export DJANGO_SETTINGS_MODULE=config.settings.production
Never commit secrets — use environment variables.
"""
from .base import *  # noqa
"""
production.py — Production settings for Render deployment.
============================================================
Extends base.py. Used on Render server only.

Set on Render dashboard (Environment tab):
    DJANGO_SETTINGS_MODULE=config.settings.production
    SECRET_KEY=<strong-random-key>
    DATABASE_URL=<neon-postgres-url>
    ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
    GOOGLE_CLIENT_ID=<from-google-cloud-console>
    GOOGLE_CLIENT_SECRET=<from-google-cloud-console>

Never commit this file with real secrets.
"""

from .base import *  # noqa: F401, F403
import environ

env = environ.Env()

# ─── Security ─────────────────────────────────────────────────────────────────
DEBUG         = False
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")


import os
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# HTTPS enforcement
SECURE_SSL_REDIRECT               = True
SECURE_HSTS_SECONDS               = 31536000     # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS    = True
SECURE_HSTS_PRELOAD               = True
SECURE_PROXY_SSL_HEADER           = ("HTTP_X_FORWARDED_PROTO", "https")

# Cookie security
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE    = True

# ─── Database ─────────────────────────────────────────────────────────────────
# Neon Postgres — connection pooling via pgbouncer URL if available
# DATABASE_URL already loaded in base.py

# Neon requires SSL — ensure sslmode=require is in your DATABASE_URL
DATABASES["default"]["OPTIONS"] = {  # type: ignore[index]
    "sslmode": "require",
}
DATABASES["default"]["CONN_MAX_AGE"] = 600  # type: ignore[index]

# ─── Email ────────────────────────────────────────────────────────────────────
# Configure SMTP for production email (allauth verification emails)
EMAIL_BACKEND       = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST          = env("EMAIL_HOST",          default="smtp.gmail.com")
EMAIL_PORT          = env.int("EMAIL_PORT",       default=587)
EMAIL_USE_TLS       = True
EMAIL_HOST_USER     = env("EMAIL_HOST_USER",     default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL  = env("DEFAULT_FROM_EMAIL",  default="noreply@faydaconverter.com")

# ─── Static Files ─────────────────────────────────────────────────────────────
# WhiteNoise serves static files directly — no nginx needed on Render
# Already configured in base.py

# ─── Allauth: enforce email verification in production ────────────────────────
ACCOUNT_EMAIL_VERIFICATION = "mandatory"

# ─── Logging: INFO in production ─────────────────────────────────────────────
LOGGING["root"]["level"] = "INFO"  # type: ignore[index]
WHITENOISE_MANIFEST_STRICT = False