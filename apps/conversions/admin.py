"""
apps/conversions/admin.py
=========================
Django admin configuration for ConversionJob and ConversionQuota.

Features:
    - ConversionJobAdmin: updated for dual-input schema (front/back files),
                          displays extraction layout approach, filters, and 
                          wipes database byte allocations cleanly.
    - ConversionQuotaAdmin: inline-friendly list with user links.
    - Custom actions: clear stale processed output bytes.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from apps.conversions.models import ConversionJob, ConversionQuota


# ─── ConversionJob ────────────────────────────────────────────────────────────

@admin.register(ConversionJob)
class ConversionJobAdmin(admin.ModelAdmin):

    # ─── List view ────────────────────────────────────────────────────────
    list_display = [
        "short_id", "user_email", "approach", "status_badge",
        "watermarked", "has_output", "created_at", "completed_at",
    ]
    list_filter  = ["status", "approach", "watermarked", "created_at"]
    search_fields = ["user__email", "input_filename_one", "input_filename_two", "error_message"]
    ordering      = ["-created_at"]
    date_hierarchy = "created_at"

    readonly_fields = [
        "id", "user", "approach", "input_filename_one", "input_filename_two",
        "status", "error_message", "watermarked",
        "created_at", "completed_at",
        "input_one_size", "input_two_size", "output_bytes_size",
    ]

    # Never show raw binary data blobs in admin forms — huge and useless
    exclude = ["input_bytes_one", "input_bytes_two", "output_bytes"]

    fieldsets = (
        (_("Job Info & Strategy"), {
            "fields": ("id", "user", "approach", "input_filename_one", "input_filename_two"),
        }),
        (_("Status"), {
            "fields": ("status", "error_message", "watermarked"),
        }),
        (_("Storage Footprint"), {
            "fields": ("input_one_size", "input_two_size", "output_bytes_size"),
        }),
        (_("Timestamps"), {
            "fields": ("created_at", "completed_at"),
        }),
    )

    # ─── Custom actions ───────────────────────────────────────────────────
    actions = ["clear_output_bytes_action"]

    @admin.action(description="Clear output bytes for selected jobs")
    def clear_output_bytes_action(self, request, queryset):
        count = 0
        for job in queryset:
            if job.output_bytes:
                job.clear_output_bytes()
                count += 1
        self.message_user(request, f"Cleared output bytes for {count} job(s).")

    # ─── Custom list columns ──────────────────────────────────────────────

    @admin.display(description="Job ID")
    def short_id(self, obj):
        return str(obj.id)[:8] + "…"

    @admin.display(description="User")
    def user_email(self, obj):
        return obj.user.email if obj.user else "— anonymous —"

    @admin.display(description="Status")
    def status_badge(self, obj):
        colours = {
            "pending":    "orange",
            "processing": "blue",
            "done":       "green",
            "failed":     "red",
        }
        colour = colours.get(obj.status, "grey")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colour, obj.status.upper(),
        )

    @admin.display(description="Output stored?", boolean=True)
    def has_output(self, obj):
        return bool(obj.output_bytes)

    @admin.display(description="Input 1 (Front) size")
    def input_one_size(self, obj):
        if obj.input_bytes_one:
            from core.utils import format_file_size
            return format_file_size(len(bytes(obj.input_bytes_one)))
        return "—"

    @admin.display(description="Input 2 (Back) size")
    def input_two_size(self, obj):
        if obj.input_bytes_two:
            from core.utils import format_file_size
            return format_file_size(len(bytes(obj.input_bytes_two)))
        return "—"

    @admin.display(description="Output size")
    def output_bytes_size(self, obj):
        if obj.output_bytes:
            from core.utils import format_file_size
            return format_file_size(len(bytes(obj.output_bytes)))
        return "—"


# ─── ConversionQuota ──────────────────────────────────────────────────────────

@admin.register(ConversionQuota)
class ConversionQuotaAdmin(admin.ModelAdmin):

    list_display  = [
        "user_email", "period", "conversions_used",
        "conversions_allowed", "remaining_display", "is_exhausted_display",
    ]
    list_filter   = ["period"]
    search_fields = ["user__email"]
    ordering      = ["user__email"]
    readonly_fields = ["user", "period", "conversions_used"]

    @admin.display(description="User")
    def user_email(self, obj):
        return obj.user.email

    @admin.display(description="Remaining")
    def remaining_display(self, obj):
        if obj.is_unlimited:
            return "∞"
        return obj.remaining

    @admin.display(description="Exhausted?", boolean=True)
    def is_exhausted_display(self, obj):
        return obj.is_exhausted