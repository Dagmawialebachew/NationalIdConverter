"""
core/mixins.py
==============
Shared Django CBV mixins used across multiple apps.

These are the cross-cutting concerns that every senior Django
developer extracts from views. Apply them via multiple inheritance
in your CBV class definition.

Usage:
    class UploadView(QuotaMixin, LoginRequiredMixin, FormView):
        ...

    class ResultView(OwnerRequiredMixin, LoginRequiredMixin, DetailView):
        ...

    class ConvertAjaxView(AjaxRequiredMixin, View):
        ...
"""

import json
import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect
from django.utils import timezone

logger = logging.getLogger(__name__)


# ─── Quota Enforcement ────────────────────────────────────────────────────────

class QuotaMixin:
    """
    Checks a user's conversion quota before allowing the view to proceed.

    How it works:
        - Unauthenticated users: checked against FREE_DAILY_LIMIT per IP (MVP: just block)
        - Authenticated free users: checked against FREE_DAILY_LIMIT per day
        - Paid subscribers: checked against their plan's conversion_limit

    Apply this BEFORE LoginRequiredMixin in the MRO so unauthenticated
    users still see the quota limit message, not just a login redirect.

    Override `get_quota_exceeded_url()` to redirect to a custom page.

    Example:
        class UploadView(QuotaMixin, LoginRequiredMixin, FormView):
            template_name = "conversions/upload.html"
    """

    quota_exceeded_message: str = (
        "You've used all your conversions for today. "
        "Upgrade your plan to convert more."
    )

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if self._is_quota_exceeded(request.user):
                messages.warning(request, self.quota_exceeded_message)
                return redirect(self.get_quota_exceeded_url())
        return super().dispatch(request, *args, **kwargs)

    def _is_quota_exceeded(self, user) -> bool:
        """
        Check if this user has exceeded their conversion quota.

        Free users:  limited by FREE_DAILY_LIMIT per day
        Paid users:  limited by their plan's conversion_limit (-1 = unlimited)

        Returns True if quota is exceeded, False if conversions remain.
        """
        from core.constants import FREE_DAILY_LIMIT, UNLIMITED
        from apps.conversions.models import ConversionQuota

        try:
            quota = ConversionQuota.objects.get(user=user)
        except ConversionQuota.DoesNotExist:
            # No quota record = new user = not exceeded
            return False

        if quota.conversions_allowed == UNLIMITED:
            return False

        if quota.conversions_allowed == FREE_DAILY_LIMIT:
            # Free tier: check daily count
            today_count = self._get_today_count(user)
            return today_count >= FREE_DAILY_LIMIT

        # Paid tier: check monthly count
        return quota.conversions_used >= quota.conversions_allowed

    # ─── UPDATED QUOTA MIXIN METHOD IN core/mixins.py ────────────────────────────

    def _get_today_count(self, user) -> int:
        """Count today's physically downloaded conversions for free-tier checks."""
        from apps.conversions.models import ConversionJob

        today = timezone.now().date()
        return ConversionJob.objects.filter(
            user=user,
            is_downloaded=True,  # Changed from status=JOB_STATUS_DONE
            created_at__date=today,
        ).count()

    def get_quota_exceeded_url(self) -> str:
        """
        URL to redirect to when quota is exceeded.
        Override in your view to go to the pricing page.
        Default: landing page pricing anchor.
        """
        from core.constants import PRICING_URL
        return PRICING_URL


# ─── Object Ownership ─────────────────────────────────────────────────────────

class OwnerRequiredMixin:
    """
    Ensures the requesting user owns the object being accessed.

    Prevents users from accessing other users' ConversionJob results
    by guessing UUID URLs.

    How it works:
        Calls get_object() and checks obj.user == request.user.
        If not owner: raises PermissionDenied (→ 403 response).

    Requirements:
        - The model must have a `user` ForeignKey to AUTH_USER_MODEL.
        - Use with LoginRequiredMixin (OwnerRequiredMixin first in MRO).

    Example:
        class ResultView(OwnerRequiredMixin, LoginRequiredMixin, DetailView):
            model = ConversionJob
            template_name = "conversions/result.html"
    """

    owner_field: str = "user"   # Field name on the model that holds the owner

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        owner = getattr(obj, self.owner_field, None)

        if owner != self.request.user:
            logger.warning(
                "OwnerRequiredMixin: user %s attempted to access object %s owned by %s",
                self.request.user,
                obj.pk,
                owner,
            )
            raise PermissionDenied("You do not have permission to access this resource.")

        return obj


# ─── AJAX / Fetch Requests ────────────────────────────────────────────────────

class AjaxRequiredMixin:
    """
    Restricts a view to AJAX/fetch requests only.

    Returns 400 JSON error if request is not via XMLHttpRequest or fetch.
    Use on views called from JavaScript upload.js.

    Example:
        class ConversionStatusView(AjaxRequiredMixin, View):
            def get(self, request, *args, **kwargs):
                ...
    """

    def dispatch(self, request, *args, **kwargs):
        if not self._is_ajax(request):
            return JsonResponse(
                {"error": "This endpoint only accepts AJAX requests.", "ok": False},
                status=400,
            )
        return super().dispatch(request, *args, **kwargs)

    @staticmethod
    def _is_ajax(request) -> bool:
        """
        Detect AJAX/fetch requests.
        Supports both old XMLHttpRequest header and modern fetch with JSON content type.
        """
        return (
            request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or request.headers.get("Accept") == "application/json"
            or request.content_type == "application/json"
        )


class AjaxResponseMixin:
    """
    Mixin that adds JSON response helpers to any CBV.
    Does NOT restrict to AJAX only — just provides the helpers.

    Provides:
        self.json_success(data, status=200)
        self.json_error(message, status=400)

    Example:
        class UploadView(AjaxResponseMixin, LoginRequiredMixin, FormView):
            def form_valid(self, form):
                ...
                return self.json_success({"redirect_url": result_url})
    """

    def json_success(self, data: dict, status: int = 200) -> JsonResponse:
        return JsonResponse({"ok": True, **data}, status=status)

    def json_error(self, message: str, status: int = 400) -> JsonResponse:
        return JsonResponse({"ok": False, "error": message}, status=status)


# ─── Paid Feature Gate ────────────────────────────────────────────────────────

class PaidPlanRequiredMixin:
    """
    Restricts access to users with an active paid subscription.

    Used for features not available on the free tier:
    - API key access
    - Bulk batch download
    - Dashboard analytics (v2)

    Redirects free users to the pricing page with a message.

    Example:
        class ApiKeyView(PaidPlanRequiredMixin, LoginRequiredMixin, TemplateView):
            template_name = "billing/api_key.html"
    """

    paid_required_message: str = (
        "This feature requires a paid plan. "
        "Upgrade to unlock unlimited conversions and more."
    )

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        if not self._has_active_subscription(request.user):
            messages.info(request, self.paid_required_message)
            from core.constants import PRICING_URL
            return redirect(PRICING_URL)

        return super().dispatch(request, *args, **kwargs)

    def _has_active_subscription(self, user) -> bool:
        """
        Check if user has a currently active, non-expired paid subscription.
        Returns False for free-tier users.
        """
        try:
            from apps.billing.models import Subscription
            from core.constants import PAYMENT_STATUS_SUCCESS

            return Subscription.objects.filter(
                user=user,
                status="active",
                expires_at__gt=timezone.now(),
            ).exists()
        except Exception:
            return False


# ─── Business Account Gate ────────────────────────────────────────────────────

class BusinessRequiredMixin:
    """
    Restricts access to users with user_type == 'business'.

    Use for business-only views like API key management
    and bulk conversion (v2 features).

    Example:
        class BusinessDashboardView(BusinessRequiredMixin, LoginRequiredMixin, TemplateView):
            ...
    """

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            from core.constants import USER_TYPE_BUSINESS
            if getattr(request.user, "user_type", None) != USER_TYPE_BUSINESS:
                raise PermissionDenied("This section is for business accounts only.")
        return super().dispatch(request, *args, **kwargs)


# ─── Page Title Helper ────────────────────────────────────────────────────────

class PageTitleMixin:
    """
    Injects a `page_title` variable into every template context.

    Set `page_title` as a class attribute or override `get_page_title()`.

    Example:
        class UploadView(PageTitleMixin, FormView):
            page_title = "Convert Your Fayda ID"
    """

    page_title: str = "Fayda ID Converter"

    def get_page_title(self) -> str:
        return self.page_title

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = self.get_page_title()
        return context