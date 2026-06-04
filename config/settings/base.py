"""
Base settings — shared across all environments.
Imported by local.py and production.py.
Never run this directly.
"""
"""
base.py — Shared settings for ALL environments.
================================================
Never run directly. Always imported by local.py or production.py.

Environment variables are loaded from .env via django-environ.
Never hardcode secrets here.
"""

from pathlib import Path
import environ

# ─── Paths ────────────────────────────────────────────────────────────────────
# BASE_DIR = fayda_converter/ (project root, where manage.py lives)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ─── Environment ──────────────────────────────────────────────────────────────
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
)
environ.Env.read_env(BASE_DIR / ".env")

# ─── Core ─────────────────────────────────────────────────────────────────────
SECRET_KEY = env("SECRET_KEY")
DEBUG      = env("DEBUG")

ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# ─── Applications ─────────────────────────────────────────────────────────────
DJANGO_APPS = [
    "jazzmin",           # Must be BEFORE django.contrib.admin
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",      # Required by allauth
]

THIRD_PARTY_APPS = [
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "crispy_forms",
    "crispy_tailwind",
]

LOCAL_APPS = [
    "core",
    "apps.landing",
    "apps.accounts",
    "apps.conversions",
    "apps.billing",
    "apps.dashboard",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ─── Middleware ────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",   # Serve static files
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",  # Required by allauth
]

# ─── URLs ─────────────────────────────────────────────────────────────────────
ROOT_URLCONF = "config.urls"

# ─── Templates ────────────────────────────────────────────────────────────────
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",  # Required by allauth
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                'apps.conversions.context_processors.credit_quota',
            ],
        },
    },
]

# ─── WSGI ─────────────────────────────────────────────────────────────────────
WSGI_APPLICATION = "config.wsgi.application"

# ─── Database ─────────────────────────────────────────────────────────────────
# Configured per environment (local.py / production.py)
# Both point to Neon Postgres via DATABASE_URL env var
DATABASES = {
    "default": env.db("DATABASE_URL"),
}

# ─── Authentication ───────────────────────────────────────────────────────────
AUTH_USER_MODEL = "accounts.CustomUser"   # Our custom user — set before any migration

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# ─── Password Validation ──────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ─── Internationalization ─────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE     = "Africa/Addis_Ababa"
USE_I18N      = True
USE_TZ        = True

# ─── Static Files ─────────────────────────────────────────────────────────────
STATIC_URL  = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ─── Default Primary Key ──────────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ─── Sites Framework (allauth) ────────────────────────────────────────────────
SITE_ID = 1

# ─── django-allauth ───────────────────────────────────────────────────────────
ACCOUNT_USER_MODEL_USERNAME_FIELD = None             # CustomUser has no username field
ACCOUNT_LOGIN_METHODS             = {"email"}        # Email-only authentication
ACCOUNT_SIGNUP_FIELDS             = ["email*", "password1*", "password2*"] # Fields required for signup
ACCOUNT_EMAIL_VERIFICATION        = "mandatory"      # Must verify email to login
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_AUTHENTICATION_METHOD = "email"
LOGIN_REDIRECT_URL                = "/convert/"      # After login → upload page
LOGOUT_REDIRECT_URL               = "/"              # After logout → landing page
LOGIN_URL                         = "/auth/login/"

# Skips the "Are you sure you want to log in with Google?" confirmation screen
SOCIALACCOUNT_LOGIN_ON_GET        = True
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
        "APP": {
            "client_id":     env("GOOGLE_CLIENT_ID",     default=""),
            "secret":        env("GOOGLE_CLIENT_SECRET", default=""),
            "key":           "",
        },
    }
}

# ─── crispy-forms ─────────────────────────────────────────────────────────────
CRISPY_ALLOWED_TEMPLATE_PACKS = "tailwind"
CRISPY_TEMPLATE_PACK          = "tailwind"

# ─── Jazzmin Admin Theme ──────────────────────────────────────────────────────
JAZZMIN_SETTINGS = {
    "site_title":        "Fayda Admin",
    "site_header":       "Fayda Converter",
    "site_brand":        "Fayda ID",
    "welcome_sign":      "Welcome to Fayda Converter Admin",
    "copyright":         "Fayda Converter",
    "search_model":      ["accounts.CustomUser"],
    "topmenu_links": [
        {"name": "Home",      "url": "admin:index"},
        {"name": "Site",      "url": "/", "new_window": True},
    ],
    "show_sidebar":              True,
    "navigation_expanded":       True,
    "hide_apps":                 ["sites"],
    "icons": {
        "auth":                         "fas fa-users-cog",
        "accounts.CustomUser":          "fas fa-user",
        "conversions.ConversionJob":    "fas fa-exchange-alt",
        "billing.Plan":                 "fas fa-tags",
        "billing.Subscription":         "fas fa-credit-card",
    },
    "default_icon_parents":  "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",
}

# ─── File Upload ──────────────────────────────────────────────────────────────
# Max upload size = 10MB (enforced in forms + middleware)
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024   # 10 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024   # 10 MB

# ─── Logging ──────────────────────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class":     "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level":    "INFO",
    },
    "loggers": {
        "django": {
            "handlers":  ["console"],
            "level":     "INFO",
            "propagate": False,
        },
        "apps.conversions": {
            "handlers":  ["console"],
            "level":     "DEBUG",
            "propagate": False,
        },
    },
}


ACCOUNT_ADAPTER = 'apps.accounts.adapters.AntiExploitAccountAdapter'


