"""
apps/accounts/signals.py
========================
Django signals for the accounts app.

Signals here:
    post_save → CustomUser
        └── create_user_quota()   — creates a ConversionQuota record
                                    for every new user

How to activate:
    In apps/accounts/apps.py, the ready() method imports this module.
    Never import signals directly in models.py or views.py.
"""

import logging

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_quota(sender, instance, created: bool, **kwargs) -> None:
    """
    Automatically create a ConversionQuota record when a new user registers.

    Called every time a CustomUser is saved. The `created` flag
    ensures we only act on INSERT, not UPDATE.

    Free tier users start with:
        conversions_allowed = FREE_DAILY_LIMIT (3)
        conversions_used    = 0
        period              = current YYYY-MM

    Args:
        sender:   The CustomUser model class
        instance: The saved CustomUser instance
        created:  True if this is a new record (INSERT), False for UPDATE
    """
    if not created:
        return  # Only run on new user creation

    try:
        from apps.conversions.models import ConversionQuota
        from core.constants import FREE_DAILY_LIMIT
        from django.utils import timezone

        period = timezone.now().strftime("%Y-%m")

        quota, was_created = ConversionQuota.objects.get_or_create(
            user=instance,
            defaults={
                "conversions_allowed": FREE_DAILY_LIMIT,
                "conversions_used":    0,
                "period":              period,
            },
        )

        if was_created:
            logger.info(
                "create_user_quota: quota created for user=%s (allowed=%d)",
                instance.email,
                FREE_DAILY_LIMIT,
            )
        else:
            # Quota already existed — shouldn't happen for new users,
            # but safe to log and continue
            logger.warning(
                "create_user_quota: quota already existed for new user=%s",
                instance.email,
            )

    except Exception as exc:
        # Never crash registration because of a quota error
        logger.exception(
            "create_user_quota: failed to create quota for user=%s: %s",
            instance.email,
            exc,
        )