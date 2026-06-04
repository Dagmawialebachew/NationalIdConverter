"""
apps/conversions/managers.py
=============================
Custom managers and querysets for the conversions app.

Keeps query logic out of views and models — all reusable
filtering lives here and is callable from anywhere.

Usage:
    ConversionJob.objects.pending()
    ConversionJob.objects.by_user(request.user)
    ConversionJob.objects.done().by_user(user).this_month()
    ConversionQuota.objects.for_user(user)
"""

from django.db import models
from django.utils import timezone


# ─── ConversionJob ────────────────────────────────────────────────────────────

class ConversionJobQuerySet(models.QuerySet):

    def pending(self):
        """Jobs waiting to be processed."""
        from core.constants import JOB_STATUS_PENDING
        return self.filter(status=JOB_STATUS_PENDING)

    def processing(self):
        """Jobs currently being converted."""
        from core.constants import JOB_STATUS_PROCESSING
        return self.filter(status=JOB_STATUS_PROCESSING)

    def done(self):
        """Successfully completed jobs."""
        from core.constants import JOB_STATUS_DONE
        return self.filter(status=JOB_STATUS_DONE)

    def failed(self):
        """Jobs that encountered an error."""
        from core.constants import JOB_STATUS_FAILED
        return self.filter(status=JOB_STATUS_FAILED)

    def by_user(self, user):
        """Filter to a specific user's jobs."""
        return self.filter(user=user)

    def anonymous(self):
        """Jobs submitted without a user account."""
        return self.filter(user__isnull=True)

    def this_month(self):
        """Jobs created in the current calendar month."""
        now = timezone.now()
        return self.filter(
            created_at__year=now.year,
            created_at__month=now.month,
        )

    def today(self):
        """Jobs created today (local date per Django's TIME_ZONE)."""
        return self.filter(created_at__date=timezone.localdate())

    def downloadable(self):
        """
        Done jobs that still have output bytes stored.
        Output is wiped after first download, so this filters
        out already-downloaded jobs.
        """
        from core.constants import JOB_STATUS_DONE
        return self.filter(
            status=JOB_STATUS_DONE,
            output_bytes__isnull=False,
        )

    def with_pdf_input(self):
        """Jobs where the original upload was a PDF."""
        from core.constants import INPUT_TYPE_PDF
        return self.filter(input_type=INPUT_TYPE_PDF)

    def with_image_input(self):
        """Jobs where the original upload was an image."""
        from core.constants import INPUT_TYPE_IMAGE
        return self.filter(input_type=INPUT_TYPE_IMAGE)

    def watermarked(self):
        """Jobs that produced a watermarked (free tier) output."""
        return self.filter(watermarked=True)

    def recent(self, limit: int = 10):
        """Most recent N jobs."""
        return self.order_by("-created_at")[:limit]


class ConversionJobManager(models.Manager):
    def get_queryset(self) -> ConversionJobQuerySet:
        return ConversionJobQuerySet(self.model, using=self._db)

    # ─── Proxy chainable methods ──────────────────────────────────────────
    def pending(self):        return self.get_queryset().pending()
    def processing(self):     return self.get_queryset().processing()
    def done(self):           return self.get_queryset().done()
    def failed(self):         return self.get_queryset().failed()
    def by_user(self, user):  return self.get_queryset().by_user(user)
    def anonymous(self):      return self.get_queryset().anonymous()
    def this_month(self):     return self.get_queryset().this_month()
    def today(self):          return self.get_queryset().today()
    def downloadable(self):   return self.get_queryset().downloadable()

    def for_user_today(self, user) -> int:
        """
        Count completed conversions for a user today.
        Used by QuotaMixin for free-tier daily limit checks.
        """
        return self.get_queryset().done().by_user(user).today().count()


# ─── ConversionQuota ──────────────────────────────────────────────────────────

class ConversionQuotaQuerySet(models.QuerySet):

    def for_user(self, user):
        """Get quota record for a specific user."""
        return self.filter(user=user)

    def unlimited(self):
        """Users with unlimited conversions (-1)."""
        from core.constants import UNLIMITED
        return self.filter(conversions_allowed=UNLIMITED)

    def exhausted(self):
        """
        Users who have used up all their allowed conversions.
        Excludes unlimited users.
        """
        from core.constants import UNLIMITED
        return self.exclude(conversions_allowed=UNLIMITED).filter(
            conversions_used__gte=models.F("conversions_allowed")
        )

    def current_period(self):
        """Quotas for the current YYYY-MM period."""
        period = timezone.now().strftime("%Y-%m")
        return self.filter(period=period)

    def stale(self):
        """
        Quotas from a previous period — need resetting.
        Used by the monthly reset management command (v2).
        """
        current_period = timezone.now().strftime("%Y-%m")
        return self.exclude(period=current_period)


class ConversionQuotaManager(models.Manager):
    def get_queryset(self) -> ConversionQuotaQuerySet:
        return ConversionQuotaQuerySet(self.model, using=self._db)

    def for_user(self, user):
        return self.get_queryset().for_user(user)

    def get_or_create_for_user(self, user):
        """
        Get the quota for a user, creating it with free-tier defaults
        if it doesn't exist yet. Safe to call multiple times.
        """
        from core.constants import FREE_DAILY_LIMIT
        period = timezone.now().strftime("%Y-%m")
        return self.get_or_create(
            user=user,
            defaults={
                "conversions_allowed": FREE_DAILY_LIMIT,
                "conversions_used":    0,
                "period":              period,
            },
        )