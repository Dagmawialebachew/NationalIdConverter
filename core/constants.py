"""
core/constants.py
=================
Single source of truth for all project-wide constants.

Import from here — never hardcode these values in apps.

Usage:
    from core.constants import MAX_UPLOAD_MB, LANDSCAPE_W, FREE_DAILY_LIMIT
"""

# ─── Output Dimensions ────────────────────────────────────────────────────────
# Standard CR80 card in landscape orientation at ~300dpi
LANDSCAPE_W: int = 1012   
LANDSCAPE_H: int = 638    
OUTPUT_DPI:  int = 300

# ─── File Upload Limits ───────────────────────────────────────────────────────
MAX_UPLOAD_MB:    int   = 10
MAX_UPLOAD_BYTES: int   = MAX_UPLOAD_MB * 1024 * 1024   # 10,485,760 bytes

# ─── Supported File Types ─────────────────────────────────────────────────────
SUPPORTED_IMAGE_MIME_TYPES: list[str] = [
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/bmp",
    "image/tiff",
]

SUPPORTED_PDF_MIME_TYPES: list[str] = [
    "application/pdf",
]

SUPPORTED_IMAGE_EXTENSIONS: set[str] = {
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff",
}

SUPPORTED_PDF_EXTENSIONS: set[str] = {
    ".pdf",
}

ALL_SUPPORTED_EXTENSIONS: set[str] = (
    SUPPORTED_IMAGE_EXTENSIONS | SUPPORTED_PDF_EXTENSIONS
)

# ─── Quota / Plans ────────────────────────────────────────────────────────────
FREE_DAILY_LIMIT:       int = 3      # Conversions per day on free tier
UNLIMITED:              int = -1     # Sentinel value for unlimited conversions

# Plan type choices — stored in billing.Plan.plan_type
PLAN_TYPE_INDIVIDUAL_MONTHLY:  str = "individual_monthly"
PLAN_TYPE_INDIVIDUAL_ONETIME:  str = "individual_onetime"
PLAN_TYPE_BUSINESS_MONTHLY:    str = "business_monthly"
PLAN_TYPE_BUSINESS_ANNUAL:     str = "business_annual"
PLAN_TYPE_ONE_TIME_CREDIT:     str = "one_time_credit"

PLAN_TYPE_CHOICES: list[tuple[str, str]] = [
    (PLAN_TYPE_INDIVIDUAL_MONTHLY, "Individual Monthly"),
    (PLAN_TYPE_INDIVIDUAL_ONETIME, "Individual One-Time"),
    (PLAN_TYPE_BUSINESS_MONTHLY,   "Business Monthly"),
    (PLAN_TYPE_BUSINESS_ANNUAL,    "Business Annual"),
    (PLAN_TYPE_ONE_TIME_CREDIT,    "One-Time Credit Pack"),
]

# ─── User Types ───────────────────────────────────────────────────────────────
USER_TYPE_INDIVIDUAL: str = "individual"
USER_TYPE_BUSINESS:   str = "business"

USER_TYPE_CHOICES: list[tuple[str, str]] = [
    (USER_TYPE_INDIVIDUAL, "Individual"),
    (USER_TYPE_BUSINESS,   "Business"),
]

# ─── Conversion Job Status ────────────────────────────────────────────────────
JOB_STATUS_PENDING:    str = "pending"
JOB_STATUS_PROCESSING: str = "processing"
JOB_STATUS_DONE:       str = "done"
JOB_STATUS_FAILED:     str = "failed"

JOB_STATUS_CHOICES: list[tuple[str, str]] = [
    (JOB_STATUS_PENDING,    "Pending"),
    (JOB_STATUS_PROCESSING, "Processing"),
    (JOB_STATUS_DONE,       "Done"),
    (JOB_STATUS_FAILED,     "Failed"),
]

# ─── Input Types ──────────────────────────────────────────────────────────────
INPUT_TYPE_PDF:   str = "pdf"
INPUT_TYPE_IMAGE: str = "image"

INPUT_TYPE_CHOICES: list[tuple[str, str]] = [
    (INPUT_TYPE_PDF,   "PDF"),
    (INPUT_TYPE_IMAGE, "Image"),
]

# ─── Payment ──────────────────────────────────────────────────────────────────
CURRENCY_ETB: str = "ETB"
CURRENCY_USD: str = "USD"

APPROACH_ONE: str = "approach_one"
APPROACH_TWO: str = "approach_two"

APPROACH_CHOICES: list[tuple[str, str]] = [
    (APPROACH_ONE, "Approach 1 (Standard Layout Extraction)"),
    (APPROACH_TWO, "Approach 2 (Alternative/Variant Extraction)"),
]

PAYMENT_STATUS_PENDING:   str = "pending"
PAYMENT_STATUS_SUCCESS:   str = "success"
PAYMENT_STATUS_FAILED:    str = "failed"
PAYMENT_STATUS_REFUNDED:  str = "refunded"

PAYMENT_STATUS_CHOICES: list[tuple[str, str]] = [
    (PAYMENT_STATUS_PENDING,  "Pending"),
    (PAYMENT_STATUS_SUCCESS,  "Success"),
    (PAYMENT_STATUS_FAILED,   "Failed"),
    (PAYMENT_STATUS_REFUNDED, "Refunded"),
]

# ─── Pricing (Birr) ───────────────────────────────────────────────────────────
# Used to seed the database via a data migration or management command
PRICING_TABLE: list[dict] = [
    {
        "name":              "Free",
        "plan_type":         PLAN_TYPE_INDIVIDUAL_MONTHLY,
        "price_birr":        0,
        "conversion_limit":  FREE_DAILY_LIMIT,  # per day
        "duration_days":     0,
        "watermarked":       True,
        "is_active":         True,
    },
    {
        "name":              "Individual Basic",
        "plan_type":         PLAN_TYPE_INDIVIDUAL_MONTHLY,
        "price_birr":        50,
        "conversion_limit":  50,
        "duration_days":     30,
        "watermarked":       False,
        "is_active":         True,
    },
    {
        "name":              "Individual Pro",
        "plan_type":         PLAN_TYPE_INDIVIDUAL_MONTHLY,
        "price_birr":        120,
        "conversion_limit":  300,
        "duration_days":     30,
        "watermarked":       False,
        "is_active":         True,
    },
    {
        "name":              "One-Time Small",
        "plan_type":         PLAN_TYPE_ONE_TIME_CREDIT,
        "price_birr":        30,
        "conversion_limit":  10,
        "duration_days":     0,   # credits never expire
        "watermarked":       False,
        "is_active":         True,
    },
    {
        "name":              "One-Time Medium",
        "plan_type":         PLAN_TYPE_ONE_TIME_CREDIT,
        "price_birr":        100,
        "conversion_limit":  40,
        "duration_days":     0,
        "watermarked":       False,
        "is_active":         True,
    },
    {
        "name":              "Business Starter",
        "plan_type":         PLAN_TYPE_BUSINESS_MONTHLY,
        "price_birr":        400,
        "conversion_limit":  500,
        "duration_days":     30,
        "watermarked":       False,
        "is_active":         True,
    },
    {
        "name":              "Business Pro",
        "plan_type":         PLAN_TYPE_BUSINESS_MONTHLY,
        "price_birr":        900,
        "conversion_limit":  UNLIMITED,
        "duration_days":     30,
        "watermarked":       False,
        "is_active":         True,
    },
    {
        "name":              "Business Annual",
        "plan_type":         PLAN_TYPE_BUSINESS_ANNUAL,
        "price_birr":        8000,
        "conversion_limit":  UNLIMITED,
        "duration_days":     365,
        "watermarked":       False,
        "is_active":         True,
    },
]

# ─── URLs / Routes ────────────────────────────────────────────────────────────
HEALTH_CHECK_URL:   str = "/health/"
UPLOAD_URL:         str = "/convert/"
LOGIN_URL:          str = "/auth/login/"
DASHBOARD_URL:      str = "/dashboard/"
PRICING_URL:        str = "/#pricing"    # Anchor on landing page (MVP)

# ─── Output file naming ───────────────────────────────────────────────────────
OUTPUT_FILENAME_TEMPLATE: str = "fayda_landscape_{job_id}.jpg"