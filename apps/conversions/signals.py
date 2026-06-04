"""
apps/conversions/signals.py
===========================
Django signals for the conversions app.

Signals:
    job_downloaded
        └── increment_quota_on_download()
                When a user explicitly triggers a download,
                increment the owner's ConversionQuota.conversions_used.

Why signals instead of doing this in the view?
    Views should only handle delivery and redirecting.
    Side effects (quota tracking, future: analytics, emails) live here.
"""

import logging
from django.dispatch import receiver, Signal

logger = logging.getLogger(__name__)

# Declare an explicit custom signal for download events
job_downloaded = Signal()


@receiver(job_downloaded)
def increment_quota_on_download(sender, job, user, **kwargs) -> None:
    """
    Increment the user's conversion quota when they successfully download their file.

    Only fires when:
        - The user is authenticated (anonymous jobs don't track quota)
    
    Uses ConversionQuota.increment() which utilizes a database-level atomic lock
    or F() expression to prevent multi-tab concurrency race conditions.
    """
    try:
        from apps.conversions.models import ConversionQuota

        # Safely get or create the tracking layer for this user
        quota, _ = ConversionQuota.objects.get_or_create_for_user(user)
        
        # Execute the atomic database increment engine
        quota.increment()

        logger.info(
            "increment_quota_on_download: user=%s used=%d allowed=%s job=%s",
            user.email,
            quota.conversions_used,
            quota.conversions_allowed,
            job.id
        )

    except Exception as exc:
        # Prevent analytics failures from crashing file delivery pipelines
        logger.exception(
            "increment_quota_on_download: failed for job=%s user=%s: %s",
            job.id,
            getattr(user, "email", "?"),
            exc,
        )