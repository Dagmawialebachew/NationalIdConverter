# # """
# # Fayda ID Converter — Project Structure Generator
# # =================================================
# # Run this ONCE after creating your Django project.

# # Step 1: Setup (run in your terminal)
# # --------------------------------------
# # # mkdir fayda_converter && cd fayda_converter
# # # python -m venv venv
# # # source venv/bin/activate          # Windows: venv\\Scripts\\activate
# # pip install django django-environ django-allauth psycopg2-binary \\
# #     django-jazzmin django-crispy-forms crispy-tailwind whitenoise \\
# #     pillow opencv-python-headless pdf2image img2pdf

# # pip freeze > requirements.txt
# # django-admin startproject config .
# # python manage.py startapp landing
# # python manage.py startapp accounts
# # python manage.py startapp conversions
# # python manage.py startapp billing
# # python manage.py startapp dashboard

# # Step 2: Run this script
# # ------------------------
# # python create_structure.py

# # What it does: creates every folder and placeholder file
# # with a docstring so you know exactly what goes in each one.
# # """

# # import os
# # from pathlib import Path

# # BASE = Path(__file__).parent
# # print(f"\\n🚀 Generating Fayda project structure in: {BASE}\\n")

# # # ─── FILES TO CREATE ──────────────────────────────────────────────────────────
# # # Format: (relative_path, content_string)

# # FILES = [

# #     # ── Config / Settings ────────────────────────────────────────────────────

# #     ("config/__init__.py", ""),

# #     ("config/settings/__init__.py", ""),

# #     ("config/settings/base.py", '''\
# # """
# # Base settings — shared across all environments.
# # Imported by local.py and production.py.
# # Never run this directly.
# # """
# # '''),

# #     ("config/settings/local.py", '''\
# # """
# # Local development settings.
# # Extends base.py.
# # Usage: export DJANGO_SETTINGS_MODULE=config.settings.local
# # """
# # from .base import *  # noqa
# # '''),

# #     ("config/settings/production.py", '''\
# # """
# # Production settings for Render deployment.
# # Extends base.py.
# # Usage: export DJANGO_SETTINGS_MODULE=config.settings.production
# # Never commit secrets — use environment variables.
# # """
# # from .base import *  # noqa
# # '''),

# #     ("config/urls.py", '''\
# # """
# # Root URL configuration.
# # Delegates routing to each app\'s urls.py.
# # Pattern: include(\'apps.appname.urls\')
# # """
# # from django.contrib import admin
# # from django.urls import path, include

# # urlpatterns = [
# #     path("admin/", admin.site.urls),
# #     # App routes added here as each app is built
# # ]
# # '''),

# #     ("config/wsgi.py", '''\
# # """WSGI entry point for production (gunicorn on Render)."""
# # import os
# # from django.core.wsgi import get_wsgi_application
# # os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
# # application = get_wsgi_application()
# # '''),

# #     ("config/asgi.py", '''\
# # """ASGI entry point — ready for async if needed later."""
# # import os
# # from django.core.asgi import get_asgi_application
# # os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
# # application = get_asgi_application()
# # '''),

# #     # ── Core — Shared utilities across all apps ───────────────────────────────

# #     ("core/__init__.py", ""),

# #     ("core/mixins.py", '''\
# # """
# # Shared Django CBV mixins used across multiple apps.

# # Classes:
# #     QuotaMixin         — checks user conversion quota before processing
# #     OwnerRequiredMixin — ensures users can only access their own objects
# #     AjaxResponseMixin  — returns JSON responses for async/fetch requests
# # """
# # '''),

# #     ("core/utils.py", '''\
# # """
# # Shared utility functions.

# # Functions:
# #     detect_file_type(file)  — returns \'pdf\' | \'image\' | \'unsupported\'
# #     validate_file_size(file, max_mb) — raises ValidationError if too large
# #     build_json_response(data, status) — consistent JSON response builder
# # """
# # '''),

# #     ("core/engine.py", '''\
# # """
# # Single import point for the Fayda conversion engine.
# # All apps import from here — never import fayda_converter_v2 directly.

# # Usage:
# #     from core.engine import convert_bytes
# #     result_bytes = convert_bytes(file_bytes, filename)
# # """
# # from fayda_converter_v2 import convert_bytes  # noqa — our engine

# # __all__ = ["convert_bytes"]
# # '''),

# #     ("core/exceptions.py", '''\
# # """
# # Custom exceptions raised by the conversion engine and caught in views.

# # Classes:
# #     QuotaExceededError      — user has used all conversions for this period
# #     UnsupportedFileTypeError — file is not a PDF or supported image format
# #     ConversionFailedError   — engine failed to process the file
# # """

# # class FaydaBaseException(Exception):
# #     """Base exception for all Fayda app errors."""
# #     pass

# # class QuotaExceededError(FaydaBaseException):
# #     """Raised when user\'s conversion quota is exhausted."""
# #     pass

# # class UnsupportedFileTypeError(FaydaBaseException):
# #     """Raised when uploaded file type is not supported."""
# #     pass

# # class ConversionFailedError(FaydaBaseException):
# #     """Raised when the conversion engine fails to process a file."""
# #     pass
# # '''),

# #     ("core/constants.py", '''\
# # """
# # Project-wide constants.

# # SUPPORTED_IMAGE_TYPES  — accepted MIME types for image upload
# # SUPPORTED_PDF_TYPES    — accepted MIME types for PDF upload
# # MAX_UPLOAD_MB          — maximum upload file size
# # LANDSCAPE_W / H        — output dimensions in pixels
# # FREE_DAILY_LIMIT       — conversions allowed on free tier per day
# # """

# # SUPPORTED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp", "image/bmp"]
# # SUPPORTED_PDF_TYPES   = ["application/pdf"]
# # MAX_UPLOAD_MB         = 10
# # LANDSCAPE_W           = 1012
# # LANDSCAPE_H           = 638
# # FREE_DAILY_LIMIT      = 3
# # '''),

# #     # ── App: landing ─────────────────────────────────────────────────────────

# #     ("apps/landing/__init__.py", ""),
# #     ("apps/landing/apps.py", '''\
# # """Landing app config."""
# # from django.apps import AppConfig

# # class LandingConfig(AppConfig):
# #     default_auto_field = "django.db.models.BigAutoField"
# #     name = "apps.landing"
# # '''),
# #     ("apps/landing/urls.py", '''\
# # """
# # Landing app URL routes.

# # GET  /          → LandingView   (homepage)
# # """
# # from django.urls import path
# # from . import views

# # app_name = "landing"

# # urlpatterns = [
# #     path("", views.LandingView.as_view(), name="home"),
# # ]
# # '''),
# #     ("apps/landing/views.py", '''\
# # """
# # Landing app views.

# # LandingView — TemplateView serving the homepage (index.html).
# #               Passes pricing plan context for the pricing section.
# #               No login required.
# # """
# # from django.views.generic import TemplateView

# # class LandingView(TemplateView):
# #     template_name = "landing/index.html"
# # '''),

# #     # ── App: accounts ────────────────────────────────────────────────────────

# #     ("apps/accounts/__init__.py", ""),
# #     ("apps/accounts/apps.py", '''\
# # """Accounts app config."""
# # from django.apps import AppConfig

# # class AccountsConfig(AppConfig):
# #     default_auto_field = "django.db.models.BigAutoField"
# #     name = "apps.accounts"
# # '''),
# #     ("apps/accounts/models.py", '''\
# # """
# # Accounts models.

# # CustomUser  — extends AbstractBaseUser.
# #               Login via email (not username) or Google OAuth.
# #               Fields: email, full_name, phone, user_type, is_verified.

# # UserManager — custom manager for CustomUser.
# #               create_user() and create_superuser() methods.
# # """
# # from django.db import models
# # from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin

# # # Models defined here in next step
# # '''),
# #     ("apps/accounts/managers.py", '''\
# # """
# # Custom manager for CustomUser.

# # UserManager:
# #     create_user(email, password, **extra_fields)
# #     create_superuser(email, password, **extra_fields)
# # """
# # from django.contrib.auth.base_user import BaseUserManager
# # '''),
# #     ("apps/accounts/forms.py", '''\
# # """
# # Accounts forms — all class-based, using Django forms.

# # CustomUserCreationForm  — registration form (email + password)
# # CustomAuthenticationForm — login form (email + password)
# # PhoneOTPForm            — phone number + OTP entry
# # ProfileUpdateForm       — update full_name, phone
# # """
# # from django import forms
# # '''),
# #     ("apps/accounts/views.py", '''\
# # """
# # Accounts views — all CBV.

# # RegisterView     — CreateView for new user registration
# # LoginView        — FormView using CustomAuthenticationForm
# # LogoutView       — RedirectView (POST only)
# # PhoneLoginView   — FormView for phone OTP entry
# # ProfileView      — LoginRequiredMixin + UpdateView
# # GoogleCallbackView — handles allauth Google OAuth callback
# # """
# # from django.views.generic import CreateView, FormView, UpdateView
# # from django.contrib.auth.mixins import LoginRequiredMixin
# # '''),
# #     ("apps/accounts/urls.py", '''\
# # """
# # Accounts URL routes.

# # POST /auth/register/        → RegisterView
# # GET  /auth/login/           → LoginView
# # POST /auth/logout/          → LogoutView
# # GET  /auth/phone/           → PhoneLoginView
# # GET  /auth/profile/         → ProfileView
# #      /auth/google/          → allauth Google OAuth (included separately)
# # """
# # from django.urls import path
# # from . import views

# # app_name = "accounts"

# # urlpatterns = [
# #     # Views wired here after each view is implemented
# # ]
# # '''),
# #     ("apps/accounts/admin.py", '''\
# # """
# # Accounts admin — CustomUser registered with full field display.
# # list_display, list_filter, search_fields all configured.
# # Password fields marked readonly.
# # """
# # from django.contrib import admin
# # from django.contrib.auth.admin import UserAdmin
# # '''),
# #     ("apps/accounts/signals.py", '''\
# # """
# # Accounts signals.

# # post_save on CustomUser:
# #     — send verification email on first registration
# #     — create free-tier quota record for new user
# # """
# # from django.db.models.signals import post_save
# # from django.dispatch import receiver
# # '''),

# #     # ── App: conversions ─────────────────────────────────────────────────────

# #     ("apps/conversions/__init__.py", ""),
# #     ("apps/conversions/apps.py", '''\
# # """Conversions app config."""
# # from django.apps import AppConfig

# # class ConversionsConfig(AppConfig):
# #     default_auto_field = "django.db.models.BigAutoField"
# #     name = "apps.conversions"
# # '''),
# #     ("apps/conversions/models.py", '''\
# # """
# # Conversions models.

# # ConversionJob   — one conversion request.
# #     Fields: user(FK), input_type(pdf|image), input_bytes(BinaryField),
# #             output_bytes(BinaryField), status(pending|processing|done|failed),
# #             created_at, completed_at, error_message.

# # ConversionQuota — tracks usage per user per period.
# #     Fields: user(FK), period(YYYY-MM), conversions_used, conversions_allowed.
# # """
# # from django.db import models
# # '''),
# #     ("apps/conversions/managers.py", '''\
# # """
# # ConversionJob custom manager.

# # Methods:
# #     pending()           — jobs with status=\'pending\'
# #     by_user(user)       — all jobs belonging to a user
# #     this_month(user)    — jobs in current calendar month for a user
# #     successful(user)    — jobs with status=\'done\' for a user
# # """
# # from django.db import models
# # '''),
# #     ("apps/conversions/forms.py", '''\
# # """
# # Conversions forms.

# # UploadForm — single FileField.
# #     Validates: file type (PDF or image), file size (max 10MB).
# #     Cleaned data passed to UploadView for processing.
# # """
# # from django import forms
# # from core.constants import MAX_UPLOAD_MB, SUPPORTED_IMAGE_TYPES, SUPPORTED_PDF_TYPES
# # '''),
# #     ("apps/conversions/views.py", '''\
# # """
# # Conversions views — all CBV.

# # UploadView      — FormView. Accepts file upload.
# #                   Uses QuotaMixin to check limit before processing.
# #                   Calls core.engine.convert_bytes().
# #                   Saves result to ConversionJob.output_bytes.
# #                   Redirects to ResultView on success.

# # ResultView      — DetailView. Shows conversion result.
# #                   OwnerRequiredMixin — user can only see own results.
# #                   Provides download button context.

# # DownloadView    — View. Streams output_bytes as file response.
# #                   Sets Content-Disposition: attachment.
# #                   OwnerRequiredMixin applied.

# # HistoryView     — LoginRequiredMixin + ListView.
# #                   Lists user\'s ConversionJob records (v2 / dashboard).
# # """
# # from django.views.generic import FormView, DetailView, View, ListView
# # from django.contrib.auth.mixins import LoginRequiredMixin
# # from core.mixins import QuotaMixin, OwnerRequiredMixin
# # '''),
# #     ("apps/conversions/urls.py", '''\
# # """
# # Conversions URL routes.

# # GET  /convert/             → UploadView
# # GET  /convert/<uuid>/      → ResultView
# # GET  /convert/<uuid>/dl/   → DownloadView
# # """
# # from django.urls import path
# # from . import views

# # app_name = "conversions"

# # urlpatterns = [
# #     # Wired after views are implemented
# # ]
# # '''),
# #     ("apps/conversions/admin.py", '''\
# # """
# # Conversions admin.

# # ConversionJobAdmin:
# #     list_display: user, input_type, status, created_at, completed_at
# #     list_filter:  status, input_type, created_at
# #     search_fields: user__email
# #     readonly_fields: input_bytes, output_bytes (too large to edit)
# # """
# # from django.contrib import admin
# # '''),
# #     ("apps/conversions/signals.py", '''\
# # """
# # Conversions signals.

# # post_save on ConversionJob (status=\'done\'):
# #     — increment ConversionQuota.conversions_used for this user + period
# # """
# # from django.db.models.signals import post_save
# # from django.dispatch import receiver
# # '''),

# #     # ── App: billing (stub — v2) ──────────────────────────────────────────────

# #     ("apps/billing/__init__.py", ""),
# #     ("apps/billing/apps.py", '''\
# # """Billing app config. Full implementation in v2."""
# # from django.apps import AppConfig

# # class BillingConfig(AppConfig):
# #     default_auto_field = "django.db.models.BigAutoField"
# #     name = "apps.billing"
# # '''),
# #     ("apps/billing/models.py", '''\
# # """
# # Billing models — stubs for v2.

# # Plan         — pricing plan (individual/business, monthly/one-time)
# # Subscription — user <> plan link, with expiry
# # OneTimeCredit — credit wallet for one-time purchases
# # Payment      — Chapa transaction record
# # """
# # from django.db import models
# # '''),
# #     ("apps/billing/views.py", '''\
# # """Billing views — implemented in v2."""
# # '''),
# #     ("apps/billing/urls.py", '''\
# # """Billing URLs — wired in v2."""
# # from django.urls import path
# # app_name = "billing"
# # urlpatterns = []
# # '''),
# #     ("apps/billing/admin.py", '''\
# # """Billing admin — implemented in v2."""
# # from django.contrib import admin
# # '''),

# #     # ── App: dashboard (stub — v2) ────────────────────────────────────────────

# #     ("apps/dashboard/__init__.py", ""),
# #     ("apps/dashboard/apps.py", '''\
# # """Dashboard app config. Full implementation in v2."""
# # from django.apps import AppConfig

# # class DashboardConfig(AppConfig):
# #     default_auto_field = "django.db.models.BigAutoField"
# #     name = "apps.dashboard"
# # '''),
# #     ("apps/dashboard/views.py", '''\
# # """
# # Dashboard views — v2.

# # DashboardHomeView — user\'s conversion history, quota usage, plan status.
# # """
# # '''),
# #     ("apps/dashboard/urls.py", '''\
# # """Dashboard URLs — wired in v2."""
# # from django.urls import path
# # app_name = "dashboard"
# # urlpatterns = []
# # '''),

# #     # ── Templates ─────────────────────────────────────────────────────────────

# #     ("templates/base.html",
# #      "<!-- Master layout. All templates extend this. Includes: navbar, footer, Tailwind CDN, messages block. -->"),
# #     ("templates/partials/_navbar.html",
# #      "<!-- Navigation bar partial. Included in base.html. -->"),
# #     ("templates/partials/_footer.html",
# #      "<!-- Footer partial. Included in base.html. -->"),
# #     ("templates/partials/_messages.html",
# #      "<!-- Django messages framework display. Flash alerts. -->"),
# #     ("templates/landing/index.html",
# #      "{% extends 'base.html' %}\n<!-- Landing page: hero, how it works, pricing, CTA. -->"),
# #     ("templates/accounts/login.html",
# #      "{% extends 'base.html' %}\n<!-- Login: email/password form + Google OAuth button + phone OTP link. -->"),
# #     ("templates/accounts/register.html",
# #      "{% extends 'base.html' %}\n<!-- Registration: name, email, password, user type selector. -->"),
# #     ("templates/accounts/profile.html",
# #      "{% extends 'base.html' %}\n<!-- Profile: update name, phone. Show plan status. -->"),
# #     ("templates/conversions/upload.html",
# #      "{% extends 'base.html' %}\n<!-- Upload page: drag & drop zone, file type hint, submit button. -->"),
# #     ("templates/conversions/result.html",
# #      "{% extends 'base.html' %}\n<!-- Result page: preview landscape ID, download button, convert another link. -->"),

# #     # ── Static ────────────────────────────────────────────────────────────────

# #     ("static/css/main.css",
# #      "/* Custom CSS — Tailwind handles most. Add only project-specific overrides here. */"),
# #     ("static/js/upload.js",
# #      "// Handles drag & drop upload UX, file preview, and progress feedback on upload.html"),
# #     ("static/img/.gitkeep", ""),

# #     # ── Root files ────────────────────────────────────────────────────────────

# #     (".env.example", """\
# # # Copy this to .env and fill in your values. Never commit .env to git.

# # DJANGO_SETTINGS_MODULE=config.settings.local
# # SECRET_KEY=your-secret-key-here
# # DEBUG=True

# # # Neon Postgres
# # DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require

# # # Google OAuth (from Google Cloud Console)
# # GOOGLE_CLIENT_ID=
# # GOOGLE_CLIENT_SECRET=

# # # Twilio (for phone OTP)
# # TWILIO_ACCOUNT_SID=
# # TWILIO_AUTH_TOKEN=
# # TWILIO_PHONE_NUMBER=

# # # Chapa (payments — v2)
# # CHAPA_SECRET_KEY=
# # """),

# #     (".gitignore", """\
# # venv/
# # __pycache__/
# # *.pyc
# # *.pyo
# # .env
# # *.sqlite3
# # media/
# # staticfiles/
# # .DS_Store
# # """),

# #     ("requirements.txt", """\
# # django>=5.0
# # django-environ
# # django-allauth
# # psycopg2-binary
# # django-jazzmin
# # django-crispy-forms
# # crispy-tailwind
# # whitenoise
# # pillow
# # opencv-python-headless
# # pdf2image
# # img2pdf
# # gunicorn
# # """),

# #     ("Procfile", "web: gunicorn config.wsgi:application --workers 2"),

# #     ("manage.py", """\
# # #!/usr/bin/env python
# # \"\"\"Django's command-line utility for administrative tasks.\"\"\"
# # import os
# # import sys

# # def main():
# #     os.environ.setdefault(\"DJANGO_SETTINGS_MODULE\", \"config.settings.local\")
# #     try:
# #         from django.core.management import execute_from_command_line
# #     except ImportError as exc:
# #         raise ImportError(
# #             \"Couldn't import Django. Activate your virtualenv.\"
# #         ) from exc
# #     execute_from_command_line(sys.argv)

# # if __name__ == \"__main__\":
# #     main()
# # """),

# #     ("fayda_converter_v2.py", """\
# # \"\"\"
# # Fayda conversion engine.
# # Place your fayda_converter_v2.py here (project root).
# # Imported via core/engine.py — never imported directly by apps.
# # \"\"\"
# # # Your existing engine code goes here
# # """),

# # ]

# # # ─── CREATE ALL FILES ─────────────────────────────────────────────────────────

# # created = skipped = 0

# # for rel_path, content in FILES:
# #     full_path = BASE / rel_path

# #     # Create parent directories
# #     full_path.parent.mkdir(parents=True, exist_ok=True)

# #     # Skip if file already exists (don't overwrite)
# #     if full_path.exists():
# #         print(f"  ⏭  exists   {rel_path}")
# #         skipped += 1
# #         continue

# #     full_path.write_text(content, encoding="utf-8")
# #     print(f"  ✓  created  {rel_path}")
# #     created += 1

# # print(f"""
# # {'─' * 52}
# # ✅  Done.
# #    Created : {created} files
# #    Skipped : {skipped} files (already existed)

# # Next step — run in your terminal:
# #    python manage.py check
# #    python manage.py migrate
# #    python manage.py runserver
# # {'─' * 52}
# # """)


# from django.core.management.utils import get_random_secret_key
# print(get_random_secret_key())
