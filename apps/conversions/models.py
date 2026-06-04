"""
apps/conversions/models.py
==========================
Core models for the Fayda conversion engine.

Models:
    ConversionJob   — tracks an extraction strategy, dual input components, 
                      and one unified landscape output.
    ConversionQuota — tracks how many conversions a user has used

Design decisions:
    - ConversionJob uses UUIDField as PK (never expose integer IDs in URLs)
    - File bytes stored directly in Postgres BinaryField (no S3 needed)
    - Files are deleted after download (handled in DownloadView)
    - Quota resets monthly (period stored as 'YYYY-MM' string)
"""

import uuid
from django.db.models import F

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.constants import (
    JOB_STATUS_CHOICES,
    JOB_STATUS_PENDING,
    FREE_DAILY_LIMIT,
    APPROACH_CHOICES,
    APPROACH_ONE,
)
from apps.conversions.managers import ConversionJobManager, ConversionQuotaManager


class ConversionJob(models.Model):
    """
    Represents one conversion request: two side/component files in, 
    one landscape JPEG out based on a specified extraction strategy.

    Lifecycle:
        pending → processing → done
                            → failed

    The UUID primary key means result URLs like /convert/result/<uuid>/
    cannot be guessed by iterating integers.
    """

    # ─── Identity ─────────────────────────────────────────────────────────
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text=_("Unique job identifier. Used in result/download URLs."),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversion_jobs",
        help_text=_("Owner of this job. Null for anonymous free-tier conversions."),
    )

    # ─── Strategy ─────────────────────────────────────────────────────────
    approach = models.CharField(
        _("extraction approach"),
        max_length=50,
        choices=APPROACH_CHOICES,
        default=APPROACH_ONE,
        help_text=_("The layout structure/strategy used to parse and combine the elements."),
    )

    # ─── Input Component One (Front Side) ─────────────────────────────────
    input_filename_one = models.CharField(
        _("original filename one"),
        max_length=255,
        blank=True,
        help_text=_("Original filename of the first component file."),
    )
    input_bytes_one = models.BinaryField(
        _("input file one bytes"),
        help_text=_("Raw bytes of the first uploaded component. Wiped after processing."),
    )

    # ─── Input Component Two (Back Side) ──────────────────────────────────
    input_filename_two = models.CharField(
        _("original filename two"),
        max_length=255,
        blank=True,
        help_text=_("Original filename of the second component file."),
    )
    input_bytes_two = models.BinaryField(
        _("input file two bytes"),
        help_text=_("Raw bytes of the second uploaded component. Wiped after processing."),
    )

    # ─── Output ───────────────────────────────────────────────────────────
    output_bytes = models.BinaryField(
        _("output file bytes"),
        null=True,
        blank=True,
        help_text=_("Raw JPEG bytes of the compiled landscape output. Wiped after download."),
    )
    
    

    # ─── Status ───────────────────────────────────────────────────────────
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=JOB_STATUS_CHOICES,
        default=JOB_STATUS_PENDING,
        db_index=True,
    )
    error_message = models.TextField(
        _("error message"),
        blank=True,
        help_text=_("Populated when status='failed'. Empty otherwise."),
    )
    watermarked = models.BooleanField(
        _("watermarked"),
        default=False,
        help_text=_("True if the output has a free-tier watermark."),
    )

    # ─── Timestamps ───────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Set when status transitions to 'done' or 'failed'."),
    )

    objects = ConversionJobManager()

    class Meta:
        verbose_name        = _("conversion job")
        verbose_name_plural = _("conversion jobs")
        ordering            = ["-created_at"]

    def __str__(self) -> str:
        user_label = self.user.email if self.user else "anonymous"
        return f"Job {str(self.id)[:8]}… [{self.status}] ({self.approach}) — {user_label}"

    # ─── Status transition helpers ────────────────────────────────────────

    def mark_processing(self) -> None:
        """Transition to 'processing'. Call before running the engine."""
        from core.constants import JOB_STATUS_PROCESSING
        self.status = JOB_STATUS_PROCESSING
        self.save(update_fields=["status"])

    def mark_done(self, output_bytes: bytes, watermarked: bool = False) -> None:
        """
        Transition to 'done'. Store output bytes and timestamp.
        Called by UploadView after a successful conversion.
        """
        from core.constants import JOB_STATUS_DONE
        self.status       = JOB_STATUS_DONE
        self.output_bytes = output_bytes
        self.watermarked  = watermarked
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "output_bytes", "watermarked", "completed_at"])

    def mark_failed(self, error: str) -> None:
        """
        Transition to 'failed'. Store the error message and timestamp.
        """
        from core.constants import JOB_STATUS_FAILED
        self.status        = JOB_STATUS_FAILED
        self.error_message = error
        self.completed_at  = timezone.now()
        self.save(update_fields=["status", "error_message", "completed_at"])

    def clear_input_bytes(self) -> None:
        """
        Wipe all raw input data components to optimize database storage footprints.
        Called by UploadView after a successful mark_done().
        """
        self.input_bytes_one = b""
        self.input_bytes_two = b""
        self.save(update_fields=["input_bytes_one", "input_bytes_two"])

    def clear_output_bytes(self) -> None:
        """
        Wipe output bytes after the user has downloaded.
        Called by DownloadView after streaming the file.
        """
        self.output_bytes = None
        self.save(update_fields=["output_bytes"])

    @property
    def is_done(self) -> bool:
        from core.constants import JOB_STATUS_DONE
        return self.status == JOB_STATUS_DONE

    @property
    def is_failed(self) -> bool:
        from core.constants import JOB_STATUS_FAILED
        return self.status == JOB_STATUS_FAILED

    @property
    def is_downloadable(self) -> bool:
        """True if the job is done AND output bytes haven't been wiped yet."""
        return self.is_done and bool(self.output_bytes)

class ConversionQuota(models.Model):
    """
    Tracks continuous credit balances for a user instead of a monthly quota.
    
    This architecture uses a continuous balance model:
      - conversions_allowed: Total lifetime credits granted or purchased.
      - conversions_used: Total lifetime credits consumed.
      - Balance remaining = conversions_allowed - conversions_used
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversion_quota",
    )
    
    # We keep 'period' so existing migrations/queries don't crash,
    # but we give it a default fallback value since we no longer use or reset it.
    period = models.CharField(
        _("period label"),
        max_length=7,
        default="LIFETIME",
        help_text=_("Legacy field retained for migration stability. Set to 'LIFETIME'."),
    )
    
    conversions_used = models.PositiveIntegerField(
        _("credits consumed"), 
        default=0,
        help_text=_("Total number of conversions this user has completed over their lifetime.")
    )
    
    conversions_allowed = models.IntegerField(
        _("credits granted"), 
        default=3,  # Gives newly registered users 3 free initial credits
        help_text=_("Total lifetime credits granted to the user. Set to -1 for unlimited access.")
    )

    objects = ConversionQuotaManager()

    class Meta:
        verbose_name        = _("conversion quota")
        verbose_name_plural = _("conversion quotas")

    def __str__(self) -> str:
        if self.is_unlimited:
            return f"{self.user.email} — Balance: Unlimited (∞)"
        return f"{self.user.email} — Balance: {self.remaining} Credits Remaining ({self.conversions_used} used)"

    # ─── Credit Balance Helpers ───────────────────────────────────────────

    @property
    def is_unlimited(self) -> bool:
        from core.constants import UNLIMITED
        return self.conversions_allowed == UNLIMITED

    @property
    def remaining(self) -> int:
        """
        Returns the real-time available conversion credit balance.
        Returns 999999 for unlimited/enterprise business accounts.
        """
        if self.is_unlimited:
            return 999_999
        return max(0, self.conversions_allowed - self.conversions_used)

    @property
    def is_exhausted(self) -> bool:
        """
        Returns True if the user has no remaining conversion credits left.
        """
        if self.is_unlimited:
            return False
        return self.conversions_used >= self.conversions_allowed

    def deduct_credit(self) -> None:
        """
        Deducts exactly 1 credit from the user's available balance.
        
        Uses Django's F() expression to update the value atomically directly at
        the database level, avoiding multi-user write race conditions.
        """
        if self.is_unlimited:
            return

        from django.db.models import F
        ConversionQuota.objects.filter(pk=self.pk).update(
            conversions_used=F("conversions_used") + 1
        )
        self.refresh_from_db()

    def add_credits(self, amount: int) -> None:
        """
        Safely increments the user's total allowed credits by a given package bundle volume.
        """
        if self.is_unlimited or amount <= 0:
            return

        from django.db.models import F
        ConversionQuota.objects.filter(pk=self.pk).update(
            conversions_allowed=F("conversions_allowed") + amount
        )
        self.refresh_from_db()
        
    def increment(self) -> None:
        """
        Atomic database-level increment to prevent multi-tab concurrency race conditions.
        Refreshes from DB afterwards to ensure Python field values match the new DB reality.
        """
        # 1. Update atomically at the database layer
        self.conversions_used = F('conversions_used') + 1
        self.save(update_fields=['conversions_used'])
        
        # 2. Reload from DB so that signals/logging can read the real updated integer
        self.refresh_from_db(fields=['conversions_used'])