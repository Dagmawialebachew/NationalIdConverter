"""
apps/accounts/admin.py
======================
Django admin configuration for CustomUser.

Features:
    - List display with key fields + quota info
    - Search by email and full name
    - Filter by user_type, is_verified, is_active
    - Fieldset layout matching the model
    - Inline quota display (read-only)
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import CustomUser


# ─── Inline: Conversion Quota ─────────────────────────────────────────────────

class ConversionQuotaInline(admin.StackedInline):
    """Show the user's quota directly on the user admin page."""
    from apps.conversions.models import ConversionQuota  # lazy to avoid circular import

    model          = ConversionQuota
    can_delete     = False
    verbose_name   = "Conversion Quota"
    readonly_fields = ["conversions_used", "conversions_allowed", "period"]
    extra          = 0

    def has_add_permission(self, request, obj=None):
        return False


# ─── CustomUser Admin ─────────────────────────────────────────────────────────

@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    """
    Admin panel configuration for CustomUser.

    Extends Django's built-in UserAdmin but replaces the username
    field references with email throughout.
    """

    # ─── List view ────────────────────────────────────────────────────────
    list_display  = [
        "email", "full_name", "user_type",
        "is_verified", "is_active", "is_staff", "date_joined",
    ]
    list_filter   = ["user_type", "is_verified", "is_active", "is_staff", "date_joined"]
    search_fields = ["email", "full_name", "phone"]
    ordering      = ["-date_joined"]

    # ─── Detail view fieldsets ────────────────────────────────────────────
    fieldsets = (
        (None, {
            "fields": ("email", "password"),
        }),
        (_("Personal info"), {
            "fields": ("full_name", "phone"),
        }),
        (_("Account type"), {
            "fields": ("user_type",),
        }),
        (_("Status"), {
            "fields": ("is_verified", "is_active", "is_staff", "is_superuser"),
        }),
        (_("Permissions"), {
            "classes": ("collapse",),
            "fields":  ("groups", "user_permissions"),
        }),
        (_("Important dates"), {
            "fields": ("last_login", "date_joined"),
        }),
    )

    # ─── Add user form fieldsets ──────────────────────────────────────────
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields":  (
                "email", "full_name", "user_type",
                "password1", "password2",
                "is_active", "is_verified",
            ),
        }),
    )

    readonly_fields = ["last_login", "date_joined"]

    # Attach quota inline — wrapped in try/except so admin loads even
    # before conversions migrations have been run
    try:
        inlines = [ConversionQuotaInline]
    except Exception:
        inlines = []