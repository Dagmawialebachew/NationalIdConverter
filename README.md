# 🪪 Fayda ID Converter

> Convert Ethiopian Digital ID (Fayda) from portrait to landscape format.
> Built with Django 5, Tailwind CSS, Neon Postgres. Deployed on Render.

---

## What This Project Does

Ethiopian citizens receive their Fayda ID from the Telebirr app in **portrait/vertical** format.
Most offices, print shops, and institutions need it in **horizontal/landscape** format.

This web app accepts:
- **e-Fayda PDF** (downloaded directly from Telebirr app)
- **Photo/screenshot** of the Fayda ID card

And outputs a clean **landscape JPG** ready to print or download.

---

## The Problem We're Solving

People in towns like Metema, Gondar, and across Ethiopia were paying 15,000+ Birr
to scammers for this conversion. We built it properly. Free tier + affordable paid plans.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5 (class-based views, signals, managers) |
| Frontend | HTML + Tailwind CSS + Vanilla JavaScript |
| Database | Neon Postgres (serverless, free tier) |
| Auth | django-allauth (Google OAuth) + Phone OTP |
| Admin | Django Admin + Jazzmin theme |
| Forms | django-crispy-forms + crispy-tailwind |
| Static files | WhiteNoise (no nginx needed) |
| Deployment | Render (free tier) |
| Keep-alive | Uptime Robot + Telegram bot pinging /health/ |
| Conversion engine | Pillow + OpenCV + pdf2image (fayda_converter_v2.py) |

---

## Project Structure

```
fayda_converter/
├── config/                         ← Django project config
│   ├── settings/
│   │   ├── base.py                 ← Shared settings (all environments)
│   │   ├── local.py                ← Dev settings (extends base)
│   │   └── production.py           ← Render settings (extends base)
│   ├── urls.py                     ← Root URL router (delegates to apps)
│   ├── wsgi.py                     ← Gunicorn entry point
│   └── asgi.py                     ← Async entry point (future)
│
├── core/                           ← Shared utilities (no models)
│   ├── mixins.py                   ← QuotaMixin, OwnerRequiredMixin, AjaxResponseMixin
│   ├── utils.py                    ← detect_file_type(), validate_file_size()
│   ├── engine.py                   ← Single import point for convert_bytes()
│   ├── exceptions.py               ← QuotaExceededError, UnsupportedFileTypeError
│   └── constants.py                ← LANDSCAPE_W/H, MAX_UPLOAD_MB, FREE_DAILY_LIMIT
│
├── apps/
│   ├── landing/                    ← Homepage (no model, TemplateView only)
│   │   ├── views.py                ← LandingView
│   │   └── urls.py
│   │
│   ├── accounts/                   ← Auth, users, profiles
│   │   ├── models.py               ← CustomUser (AbstractBaseUser, email login)
│   │   ├── managers.py             ← UserManager
│   │   ├── forms.py                ← Registration, login, profile forms
│   │   ├── views.py                ← RegisterView, LoginView, ProfileView (all CBV)
│   │   ├── urls.py
│   │   ├── admin.py                ← CustomUserAdmin
│   │   └── signals.py              ← Create quota on user creation
│   │
│   ├── conversions/                ← CORE MVP APP
│   │   ├── models.py               ← ConversionJob, ConversionQuota
│   │   ├── managers.py             ← pending(), by_user(), this_month()
│   │   ├── forms.py                ← UploadForm (validates type + size)
│   │   ├── views.py                ← UploadView, ResultView, DownloadView (all CBV)
│   │   ├── urls.py
│   │   ├── admin.py                ← ConversionJobAdmin
│   │   └── signals.py              ← Increment quota on job completion
│   │
│   ├── billing/                    ← Plans + payments (v2 — stub only in MVP)
│   │   ├── models.py               ← Plan, Subscription, OneTimeCredit, Payment
│   │   └── ...
│   │
│   └── dashboard/                  ← User history + stats (v2 — stub only in MVP)
│       └── ...
│
├── templates/
│   ├── base.html                   ← Master layout (Tailwind, navbar, footer, messages)
│   ├── partials/
│   │   ├── _navbar.html
│   │   ├── _footer.html
│   │   └── _messages.html
│   ├── landing/index.html          ← Hero, how it works, pricing, CTA
│   ├── accounts/
│   │   ├── login.html              ← Email + Google OAuth button
│   │   ├── register.html
│   │   └── profile.html
│   └── conversions/
│       ├── upload.html             ← Drag & drop zone
│       └── result.html             ← Preview + download button
│
├── static/
│   ├── css/main.css                ← Custom overrides (Tailwind handles most)
│   ├── js/upload.js                ← Drag & drop UX + progress feedback
│   └── img/
│
├── fayda_converter_v2.py           ← Conversion engine (Pillow + OpenCV + pdf2image)
├── manage.py
├── requirements.txt
├── Procfile                        ← gunicorn config.wsgi:application --workers 2
├── .env.example                    ← Copy to .env and fill in secrets
└── .gitignore
```

---

## Database Schema

### `accounts.CustomUser`
| Field | Type | Notes |
|---|---|---|
| id | BigAutoField | PK |
| email | EmailField | Unique, used as login username |
| full_name | CharField | |
| phone | CharField | Optional, for OTP login |
| user_type | CharField | `individual` or `business` |
| is_verified | BooleanField | Email verification status |
| is_active | BooleanField | |
| is_staff | BooleanField | |
| date_joined | DateTimeField | |

### `conversions.ConversionJob`
| Field | Type | Notes |
|---|---|---|
| id | UUIDField | PK (UUID not integer — secure URL) |
| user | FK → CustomUser | null=True (allow anonymous free tier) |
| input_type | CharField | `pdf` or `image` |
| input_bytes | BinaryField | Raw uploaded file bytes |
| output_bytes | BinaryField | Converted landscape image bytes |
| status | CharField | `pending`, `processing`, `done`, `failed` |
| error_message | TextField | Populated on failure |
| created_at | DateTimeField | auto_now_add |
| completed_at | DateTimeField | null=True |

### `conversions.ConversionQuota`
| Field | Type | Notes |
|---|---|---|
| user | OneToOneField → CustomUser | |
| period | CharField | `YYYY-MM` (resets monthly) |
| conversions_used | IntegerField | Incremented by signal |
| conversions_allowed | IntegerField | Set by plan (-1 = unlimited) |

### `billing.Plan` (v2)
| Field | Type | Notes |
|---|---|---|
| name | CharField | e.g. "Individual Pro" |
| plan_type | CharField | `individual_monthly`, `business_monthly`, `one_time` |
| price_birr | DecimalField | ETB price |
| conversion_limit | IntegerField | -1 = unlimited |
| duration_days | IntegerField | 30, 365, or 0 (one-time) |
| is_active | BooleanField | |

---

## Pricing Packages

| Plan | Type | Price | Conversions | Target |
|---|---|---|---|---|
| Free | — | 0 Birr | 3/day, watermarked | Anyone testing |
| Individual Basic | Monthly | 50 Birr/mo | 50/month | Students |
| Individual Pro | Monthly | 120 Birr/mo | 300/month | Frequent users |
| One-Time Small | Credit | 30 Birr | 10 credits | One-off need |
| One-Time Medium | Credit | 100 Birr | 40 credits | Occasional use |
| Business Starter | Monthly | 400 Birr/mo | 500/month | Small offices |
| Business Pro | Monthly | 900 Birr/mo | Unlimited | Print shops |
| Business Annual | Annual | 8,000 Birr/yr | Unlimited | Lock-in deal |

---

## User Flows

**Individual:**
Register → Free tier (3/day) → Hit limit → Upgrade prompt → Chapa payment → Unlimited within plan

**Business:**
Register → Select Business type → Choose plan → Chapa pay → API key for bulk use

**One-time (no account required for MVP):**
Upload → Pay 30 Birr via Chapa → Download → Optionally save account

---

## MVP Scope (Build First)

The MVP is 3 things only:
1. **Landing page** — looks professional, explains the service
2. **Upload page** — drag & drop PDF or image
3. **Result page** — download the landscape ID

Everything else (billing, dashboard, bot) is v2.

---

## Local Development Setup

```bash
# 1. Clone and enter
git clone <your-repo> fayda_converter
cd fayda_converter

# 2. Virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Environment variables
cp .env.example .env
# Edit .env and fill in:
#   SECRET_KEY, DATABASE_URL, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET

# 5. Database
python manage.py migrate

# 6. Create superuser (for admin panel)
python manage.py createsuperuser

# 7. Run
python manage.py runserver
```

Visit: http://localhost:8000

---

## Render Deployment

```bash
# Build command (set in Render dashboard)
pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate

# Start command
gunicorn config.wsgi:application --workers 2

# Environment variables (set in Render dashboard)
DJANGO_SETTINGS_MODULE=config.settings.production
SECRET_KEY=<generate a strong key>
DATABASE_URL=<neon postgres connection string>
ALLOWED_HOSTS=yourapp.onrender.com
GOOGLE_CLIENT_ID=<from google cloud console>
GOOGLE_CLIENT_SECRET=<from google cloud console>
```

---

## Keep-Alive Strategy

Render free tier sleeps after 15 minutes of inactivity.

Two-layer protection:
1. **Uptime Robot** — pings `https://yourapp.onrender.com/health/` every 5 minutes
2. **Telegram bot** — running separately, also pings `/health/` every 14 minutes

The `/health/` endpoint returns `{"status": "ok"}` instantly — no DB query.

---

## Environment Variables Reference

```bash
# Required always
DJANGO_SETTINGS_MODULE=config.settings.local    # or production
SECRET_KEY=your-very-long-random-secret-key
DATABASE_URL=postgresql://user:pass@host/db?sslmode=require

# Google OAuth (get from Google Cloud Console)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# Email (production only)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=noreply@faydaconverter.com

# Chapa payments (v2)
CHAPA_SECRET_KEY=

# Twilio phone OTP (v2)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=
```

---

## Build Roadmap

### ✅ Done
- [x] Conversion engine (`fayda_converter_v2.py`) — PDF + image → landscape
- [x] Project structure generator (`create_structure.py`) — 65 files
- [x] `config/` — all settings files (base, local, production)
- [x] `config/urls.py` — root URL router
- [x] `config/wsgi.py` + `config/asgi.py`
- [x] Schema design (all models planned)
- [x] Pricing packages designed
- [x] Architecture decided (Django + Tailwind + Neon + Render)

### 🔨 Next — Build in This Order

#### Phase 1: Foundation
- [ ] `core/exceptions.py` — custom exceptions
- [ ] `core/constants.py` — shared constants
- [ ] `core/mixins.py` — QuotaMixin, OwnerRequiredMixin
- [ ] `core/engine.py` — import wrapper for convert_bytes()
- [ ] `core/utils.py` — file validators

#### Phase 2: Accounts App
- [ ] `apps/accounts/managers.py` — UserManager
- [ ] `apps/accounts/models.py` — CustomUser model
- [ ] Run `python manage.py makemigrations accounts`
- [ ] `apps/accounts/admin.py` — CustomUserAdmin
- [ ] `apps/accounts/forms.py` — Registration + login forms
- [ ] `apps/accounts/views.py` — RegisterView, LoginView, LogoutView
- [ ] `apps/accounts/urls.py` — wire views
- [ ] `apps/accounts/signals.py` — create quota on user save

#### Phase 3: Conversions App (MVP Heart)
- [ ] `apps/conversions/managers.py` — custom querysets
- [ ] `apps/conversions/models.py` — ConversionJob, ConversionQuota
- [ ] Run `python manage.py makemigrations conversions`
- [ ] `apps/conversions/forms.py` — UploadForm with validation
- [ ] `apps/conversions/views.py` — UploadView, ResultView, DownloadView
- [ ] `apps/conversions/urls.py` — wire views
- [ ] `apps/conversions/admin.py` — ConversionJobAdmin
- [ ] `apps/conversions/signals.py` — increment quota on done

#### Phase 4: Templates + UI
- [ ] `templates/base.html` — Tailwind master layout
- [ ] `templates/partials/_navbar.html`
- [ ] `templates/partials/_footer.html`
- [ ] `templates/partials/_messages.html`
- [ ] `templates/landing/index.html` — homepage
- [ ] `templates/accounts/login.html`
- [ ] `templates/accounts/register.html`
- [ ] `templates/conversions/upload.html` — drag & drop
- [ ] `templates/conversions/result.html` — download page
- [ ] `static/js/upload.js` — drag & drop UX

#### Phase 5: Deploy
- [ ] Push to GitHub
- [ ] Connect Render to GitHub repo
- [ ] Set all environment variables on Render
- [ ] Set up Neon DB and copy DATABASE_URL
- [ ] Configure Google OAuth (add Render URL to Google Cloud Console)
- [ ] Set up Uptime Robot monitor on `/health/`
- [ ] Test full flow: upload PDF → download landscape

#### Phase 6: v2 Features (after MVP ships)
- [ ] `apps/billing/` — Plan, Subscription, Payment models
- [ ] Chapa payment integration
- [ ] `apps/dashboard/` — usage history, quota display
- [ ] Telegram bot v2 (user-facing, not just keep-alive)
- [ ] Phone OTP login (Twilio)
- [ ] Business accounts + API key access

---

## Key Decisions Made

| Decision | Choice | Reason |
|---|---|---|
| Login method | Google OAuth + Phone OTP | Most Ethiopians use Google; phone for rural users |
| File storage | Neon Postgres `BinaryField` | No S3 needed, files deleted after download |
| Business accounts | One login per business | Simpler for MVP |
| Frontend | Tailwind CSS (no React) | Faster to build, no build step needed |
| Deployment | Render free tier | Free, real server, persistent, not serverless |
| Bot role | Keep-alive only (v1) | Ship web app first, bot as distribution v2 |
| API layer | Django handles everything | No separate FastAPI needed for MVP |

---

## Architecture Notes for the Next Developer

**Do not use function-based views.** Everything is CBV (Class-Based Views).

**Mixins over repetition.** `QuotaMixin` and `OwnerRequiredMixin` in `core/mixins.py`
are used on every conversion view. Add new cross-cutting concerns as mixins there.

**Never import the engine directly.** Always import from `core.engine`:
```python
from core.engine import convert_bytes   # ✅ correct
from fayda_converter_v2 import convert_bytes  # ❌ wrong
```

**Signals handle side effects.** Quota incrementing, welcome emails — all in `signals.py`,
not in views. Views just convert and redirect.

**UUID primary keys on ConversionJob.** Never expose integer IDs in URLs for conversion
results. Users should not be able to guess other users' job IDs.

**TIME_ZONE = Africa/Addis_Ababa.** All timestamps stored in UTC, displayed in EAT.

---

## Contact & Ownership

Built by: [Your name]
Project started: May 2026
Status: MVP in development