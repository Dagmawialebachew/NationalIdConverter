import base64
import uuid
from django.conf import settings
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

PLAN_TIERS = (
    ('starter', 'Starter Plan (1 Credit)'),
    ('plus', 'Plus Plan (2 Credits)'),
    ('basic', 'Basic Plan (12 Credits)'),
    ('standard', 'Standard Plan (40 Credits)'),
    ('printing-pro', 'Printing Pro Package (150 Credits)'),
    ('enterprise', 'Enterprise Plan (700 Credits)'),
)

VERIFICATION_STATUS = (
    ('pending', 'Pending Verification'),
    ('approved', 'Approved & Credited'),
    ('rejected', 'Rejected/Invalid'),
)

class PaymentVerification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payment_receipts"
    )
    plan_tier = models.CharField(max_length=30, choices=PLAN_TIERS)
    transaction_reference = models.CharField(
        _("Transaction Ref / Reference Number"),
        max_length=100,
        unique=True,
        null=True,   
        blank=True,  
        help_text=_("The unique transaction reference ID from Telebirr, CBE, or Bank transfer.")
    )
    status = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='pending')
    receipt_image_base64 = models.TextField(
        _("Receipt Image String"),
        help_text=_("Base64 string representing the compressed image verification proof.")
    )
    admin_notes = models.TextField(blank=True, help_text=_("Notes from checking staff members."))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Payment Verification")
        verbose_name_plural = _("Payment Verifications")

    def __str__(self) -> str:
        return f"{self.user.email} - {self.get_plan_tier_display()} ({self.status})"

    def save(self, *args, **kwargs):
        is_approving = False

        # Detect transition from a non-approved state to 'approved'
        if self.pk:
            try:
                old_obj = PaymentVerification.objects.get(pk=self.pk)
                if old_obj.status != 'approved' and self.status == 'approved':
                    is_approving = True
            except PaymentVerification.DoesNotExist:
                if self.status == 'approved':
                    is_approving = True
        else:
            if self.status == 'approved':
                is_approving = True

        # 1. Persist the payment record adjustments first
        super().save(*args, **kwargs)

        # 2. Run your atomic credit allocation engine
        if is_approving:
            from apps.conversions.models import ConversionQuota
            
            with transaction.atomic():
                # select_for_update prevents concurrent database race conditions
                quota, created = ConversionQuota.objects.select_for_update().get_or_create(user=self.user)
                
                credits_map = {
                    'starter': 1,
                    'plus': 2,
                    'basic': 12,
                    'standard': 40,
                    'printing-pro': 150,
                    'enterprise': 700,
                }
                
                added_amount = credits_map.get(self.plan_tier, 0)
                
                # Safeguard against legacy configurations or Unlimited metrics (-1)
                if quota.conversions_allowed == -1:
                    return
                
                current_credits = quota.conversions_allowed or 0
                quota.conversions_allowed = current_credits + added_amount
                quota.save(update_fields=['conversions_allowed'])