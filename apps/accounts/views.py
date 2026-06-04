"""
apps/accounts/views.py
======================
All class-based views for the accounts app.

Views:
    RegisterView      — new user sign-up
    LoginView         — email + password login
    LogoutView        — POST-only logout
    ProfileView       — view + update profile
    ChangePasswordView — authenticated password change

All views are CBVs. No function-based views.
"""

import logging

from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash, get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, FormView, TemplateView, UpdateView, View

from core.mixins import PageTitleMixin
from apps.accounts.forms import (
    RegisterForm,
    LoginForm,
    ProfileForm,
    ChangePasswordForm,
)

logger = logging.getLogger(__name__)
User   = get_user_model()


# ─── Register ─────────────────────────────────────────────────────────────────
# apps/accounts/views.py

class RegisterView(PageTitleMixin, CreateView):
    """
    New user registration with strict email confirmation workflow.
    """
    form_class     = RegisterForm
    template_name  = "accounts/register.html"
    
    # Redirect directly to allauth's verification sent page view
    success_url    = reverse_lazy("account_email_verification_sent")
    page_title     = "Create Your Account"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("conversions:upload")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # This saves the record into the DB
        user = form.save()
        
        # NOTE: Do NOT use the django login() method here. 
        # Leaving them unauthenticated forces them to check their inbox.
        
        messages.info(
            self.request,
            "Account created successfully! A verification link has been sent. Please check your inbox before logging in."
        )
        logger.info("RegisterView: pending activation user initialized email=%s", user.email)
        return redirect(self.success_url)

    def form_invalid(self, form):
        messages.error(
            self.request,
            "Please fix the errors below."
        )
        return super().form_invalid(form)


# ─── Login ────────────────────────────────────────────────────────────────────

class LoginView(PageTitleMixin, FormView):
    """
    Email + password login.

    Handles the `next` query parameter so protected views redirect
    back correctly after login.
    """

    form_class    = LoginForm
    template_name = "accounts/login.html"
    page_title    = "Sign In"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(self._get_success_url())
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        user        = form.get_user()
        remember_me = form.cleaned_data.get("remember_me", False)

        login(self.request, user)

        # If "remember me" is NOT checked, expire session when browser closes
        if not remember_me:
            self.request.session.set_expiry(0)

        messages.success(
            self.request,
            f"Welcome back, {user.display_name}!"
        )
        logger.info("LoginView: user logged in email=%s", user.email)

        return redirect(self._get_success_url())

    def form_invalid(self, form):
        # Error message comes from the form's ValidationError
        return super().form_invalid(form)

    def _get_success_url(self) -> str:
        """Honour ?next= redirect, fall back to upload page."""
        next_url = self.request.GET.get("next") or self.request.POST.get("next")
        if next_url and next_url.startswith("/"):   # basic open-redirect guard
            return next_url
        return reverse_lazy("conversions:upload")


# ─── Logout ───────────────────────────────────────────────────────────────────

class LogoutView(View):
    """
    POST-only logout view.

    GET requests are ignored (security best practice — prevents
    CSRF-free logout via link).

    Template usage:
        <form method="post" action="{% url 'accounts:logout' %}">
            {% csrf_token %}
            <button type="submit">Sign Out</button>
        </form>
    """

    def post(self, request, *args, **kwargs):
        display = request.user.display_name if request.user.is_authenticated else "User"
        logout(request)
        messages.info(request, f"You've been signed out, {display}.")
        logger.info("LogoutView: user signed out")
        return redirect("landing:index")

    def get(self, request, *args, **kwargs):
        # Silently redirect GET requests (don't log out on link click)
        return redirect("landing:index")


# ─── Profile ──────────────────────────────────────────────────────────────────

class ProfileView(PageTitleMixin, LoginRequiredMixin, UpdateView):
    """
    View and update the logged-in user's profile.

    Uses UpdateView so the form is pre-populated with existing values.
    On success: stays on the profile page with a success message.
    """

    form_class    = ProfileForm
    template_name = "accounts/profile.html"
    success_url   = reverse_lazy("accounts:profile")
    page_title    = "Your Profile"

    def get_object(self, queryset=None):
        """Always edit the currently logged-in user — never accept a pk."""
        return self.request.user

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Profile updated successfully.")
        logger.info("ProfileView: profile updated user=%s", self.request.user.email)
        return redirect(self.success_url)

    def form_invalid(self, form):
        messages.error(self.request, "Please fix the errors below.")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Attach quota info for display in the profile template
        try:
            from apps.conversions.models import ConversionQuota
            context["quota"] = ConversionQuota.objects.get(user=self.request.user)
        except Exception:
            context["quota"] = None

        return context


# ─── Change Password ──────────────────────────────────────────────────────────

class ChangePasswordView(PageTitleMixin, LoginRequiredMixin, FormView):
    """
    Authenticated password change.

    Uses update_session_auth_hash() so the user stays logged in
    after changing their password (Django logs them out otherwise).
    """

    form_class    = ChangePasswordForm
    template_name = "accounts/change_password.html"
    success_url   = reverse_lazy("accounts:profile")
    page_title    = "Change Password"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        # Keep the session alive after password change
        update_session_auth_hash(self.request, form.user)
        messages.success(self.request, "Your password has been updated.")
        logger.info("ChangePasswordView: password changed user=%s", self.request.user.email)
        return redirect(self.success_url)

    def form_invalid(self, form):
        messages.error(self.request, "Please fix the errors below.")
        return super().form_invalid(form)