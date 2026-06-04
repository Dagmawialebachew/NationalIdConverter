"""
apps/accounts/managers.py
=========================
Custom manager for CustomUser.

Why a custom manager?
    Django's default UserManager uses `username` as the login field.
    We use `email` as the primary identifier, so we need our own
    create_user() and create_superuser() that require email, not username.

Usage (automatic — Django uses this via AUTH_USER_MODEL):
    User = get_user_model()
    user = User.objects.create_user(email="user@example.com", password="secret")
    admin = User.objects.create_superuser(email="admin@example.com", password="secret")
"""

from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """
    Custom manager for CustomUser where email is the unique identifier
    for authentication instead of username.
    """

    def create_user(self, email: str, password: str = None, **extra_fields) -> "CustomUser":  # noqa: F821
        """
        Create and save a regular user with the given email and password.

        Args:
            email:         User's email address (required, used for login)
            password:      Raw password (will be hashed)
            **extra_fields: Any additional CustomUser fields
                            (full_name, phone, user_type, etc.)

        Returns:
            Saved CustomUser instance

        Raises:
            ValueError: if email is not provided

        Example:
            user = User.objects.create_user(
                email="abebe@example.com",
                password="strongpassword",
                full_name="Abebe Kebede",
                user_type="individual",
            )
        """
        if not email:
            raise ValueError(_("An email address is required."))

        email = self.normalize_email(email)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_active", True)

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str, **extra_fields) -> "CustomUser":  # noqa: F821
        """
        Create and save a superuser with full admin access.

        Args:
            email:    Email address
            password: Raw password (will be hashed)

        Returns:
            Saved CustomUser with is_staff=True, is_superuser=True

        Raises:
            ValueError: if is_staff or is_superuser are explicitly set to False

        Usage (terminal):
            python manage.py createsuperuser
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(email, password, **extra_fields)

    # ─── Custom QuerySets ─────────────────────────────────────────────────────

    def individual_users(self):
        """Return all users with user_type='individual'."""
        from core.constants import USER_TYPE_INDIVIDUAL
        return self.filter(user_type=USER_TYPE_INDIVIDUAL)

    def business_users(self):
        """Return all users with user_type='business'."""
        from core.constants import USER_TYPE_BUSINESS
        return self.filter(user_type=USER_TYPE_BUSINESS)

    def verified(self):
        """Return all users who have verified their email."""
        return self.filter(is_verified=True)

    def active_users(self):
        """Return all active, non-staff users."""
        return self.filter(is_active=True, is_staff=False)