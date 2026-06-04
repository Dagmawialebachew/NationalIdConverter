"""
apps/accounts/models.py
=======================
CustomUser — replaces Django's default User model.

Uses email as the login identifier (no username field).
Wired up in settings.py via AUTH_USER_MODEL = 'accounts.CustomUser'.

IMPORTANT: Run migrations after any field change:
    python manage.py makemigrations accounts
    python manage.py migrate
"""

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.constants import USER_TYPE_CHOICES, USER_TYPE_INDIVIDUAL
from apps.accounts.managers import UserManager


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model with email login.

    AbstractBaseUser gives us: password, last_login, is_active
    PermissionsMixin gives us: is_superuser, groups, user_permissions
    """

    # ─── Core identity ────────────────────────────────────────────────────
    email = models.EmailField(
        _("email address"),
        unique=True,
        help_text=_("Used as the login identifier."),
    )
    full_name = models.CharField(
        _("full name"),
        max_length=150,
        blank=True,
    )
    phone = models.CharField(
        _("phone number"),
        max_length=20,
        blank=True,
        help_text=_("Optional. Used for OTP login (v2)."),
    )

    # ─── Account type ─────────────────────────────────────────────────────
    user_type = models.CharField(
        _("user type"),
        max_length=20,
        choices=USER_TYPE_CHOICES,
        default=USER_TYPE_INDIVIDUAL,
    )

    # ─── Status flags ─────────────────────────────────────────────────────
    is_verified = models.BooleanField(
        _("email verified"),
        default=False,
        help_text=_("Designates whether the user has verified their email address."),
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
    )
    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Designates whether the user can log into the admin site."),
    )

    # ─── Timestamps ───────────────────────────────────────────────────────
    date_joined = models.DateTimeField(
        _("date joined"),
        default=timezone.now,
    )

    # ─── Manager ──────────────────────────────────────────────────────────
    objects = UserManager()

    # ─── Auth config ──────────────────────────────────────────────────────
    USERNAME_FIELD  = "email"       # used for login
    REQUIRED_FIELDS = ["full_name"] # asked by createsuperuser (besides email+password)

    class Meta:
        verbose_name        = _("user")
        verbose_name_plural = _("users")
        ordering            = ["-date_joined"]

    # ─── String representation ────────────────────────────────────────────
    def __str__(self) -> str:
        return self.email

    # ─── Convenience properties ───────────────────────────────────────────
    @property
    def display_name(self) -> str:
        """Full name if set, otherwise the email prefix."""
        return self.full_name or self.email.split("@")[0]

    @property
    def is_business(self) -> bool:
        from core.constants import USER_TYPE_BUSINESS
        return self.user_type == USER_TYPE_BUSINESS

    @property
    def is_individual(self) -> bool:
        return self.user_type == USER_TYPE_INDIVIDUAL

    def get_full_name(self) -> str:
        """Required by Django's auth machinery."""
        return self.full_name

    def get_short_name(self) -> str:
        """Required by Django's auth machinery."""
        return self.full_name.split()[0] if self.full_name else self.email.split("@")[0]