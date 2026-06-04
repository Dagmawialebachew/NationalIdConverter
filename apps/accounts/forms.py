"""
apps/accounts/forms.py
======================
All forms for the accounts app.

Forms:
    RegisterForm    — new user sign-up (email + password + user_type)
    LoginForm       — email + password login
    ProfileForm     — update full_name, phone, user_type
    ChangePasswordForm — authenticated password change

All forms use crispy-forms + crispy-tailwind for rendering.
In templates, just call: {% crispy form %}
"""

from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import PasswordChangeForm
from django.utils.translation import gettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Submit, Div, HTML

from core.constants import USER_TYPE_CHOICES, USER_TYPE_INDIVIDUAL

User = get_user_model()


# ─── Shared crispy helper factory ─────────────────────────────────────────────

def _make_helper(submit_text: str = "Submit", form_id: str = "") -> FormHelper:
    """Create a standard crispy FormHelper with Tailwind styling."""
    helper = FormHelper()
    helper.form_method = "post"
    helper.form_id     = form_id
    helper.attrs       = {"novalidate": True}
    helper.add_input(Submit("submit", submit_text, css_class=(
        "w-full bg-green-600 hover:bg-green-700 text-white font-semibold "
        "py-3 px-4 rounded-lg transition-colors duration-200 cursor-pointer"
    )))
    return helper


# ─── Register ─────────────────────────────────────────────────────────────────

class RegisterForm(forms.ModelForm):
    """
    New user registration form.

    Fields:
        full_name   — display name
        email       — login identifier (must be unique)
        user_type   — individual or business
        password1   — password
        password2   — password confirmation
    """

    password1 = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={
            "placeholder": "Create a password",
            "autocomplete": "new-password",
        }),
        min_length=8,
        help_text=_("At least 8 characters."),
    )
    password2 = forms.CharField(
        label=_("Confirm password"),
        widget=forms.PasswordInput(attrs={
            "placeholder": "Repeat your password",
            "autocomplete": "new-password",
        }),
    )

    class Meta:
        model  = User
        fields = ["full_name", "email", "user_type"]
        widgets = {
            "full_name": forms.TextInput(attrs={"placeholder": "Abebe Girma"}),
            "email":     forms.EmailInput(attrs={"placeholder": "you@example.com"}),
            "user_type": forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["full_name"].required = True
        self.fields["user_type"].initial  = USER_TYPE_INDIVIDUAL

        self.helper = _make_helper("Create Account", form_id="register-form")
        self.helper.layout = Layout(
            Field("full_name",  css_class="form-input"),
            Field("email",      css_class="form-input"),
            Field("user_type",  css_class="form-select"),
            Field("password1",  css_class="form-input"),
            Field("password2",  css_class="form-input"),
        )

    def clean_email(self):
        email = self.cleaned_data.get("email", "").lower().strip()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                _("An account with this email already exists.")
            )
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", _("Passwords do not match."))
        return cleaned

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


# ─── Login ────────────────────────────────────────────────────────────────────

class LoginForm(forms.Form):
    """
    Email + password login form.

    Does NOT subclass AuthenticationForm so we control the field
    names and error messages precisely.
    The authenticated user object is available as form.get_user()
    after calling form.is_valid().
    """

    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(attrs={
            "placeholder": "you@example.com",
            "autofocus":   True,
        }),
    )
    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={"placeholder": "Your password"}),
    )
    remember_me = forms.BooleanField(
        label=_("Keep me logged in"),
        required=False,
        initial=False,
    )

    def __init__(self, request=None, *args, **kwargs):
        self.request       = request
        self._cached_user  = None
        super().__init__(*args, **kwargs)

        self.helper = _make_helper("Sign In", form_id="login-form")
        self.helper.layout = Layout(
            Field("email",       css_class="form-input"),
            Field("password",    css_class="form-input"),
            Field("remember_me"),
        )

    def clean(self):
        cleaned  = super().clean()
        email    = cleaned.get("email", "").lower().strip()
        password = cleaned.get("password")

        if email and password:
            user = authenticate(self.request, username=email, password=password)
            if user is None:
                raise forms.ValidationError(
                    _("Invalid email or password. Please try again.")
                )
            if not user.is_active:
                raise forms.ValidationError(
                    _("Your account has been deactivated. Contact support.")
                )
            self._cached_user = user

        return cleaned

    def get_user(self) -> User:
        """Return the authenticated user after is_valid() == True."""
        return self._cached_user


# ─── Profile ──────────────────────────────────────────────────────────────────

class ProfileForm(forms.ModelForm):
    """
    Update profile fields for an existing user.
    Does NOT touch password or email (those have dedicated flows).
    """

    class Meta:
        model  = User
        fields = ["full_name", "phone", "user_type"]
        widgets = {
            "full_name": forms.TextInput(attrs={"placeholder": "Your full name"}),
            "phone":     forms.TextInput(attrs={"placeholder": "+251 91 234 5678"}),
            "user_type": forms.Select(),
        }
        help_texts = {
            "phone": _("Optional. Will be used for OTP login when available."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = _make_helper("Save Changes", form_id="profile-form")
        self.helper.layout = Layout(
            Field("full_name", css_class="form-input"),
            Field("phone",     css_class="form-input"),
            Field("user_type", css_class="form-select"),
        )


# ─── Change Password ──────────────────────────────────────────────────────────

class ChangePasswordForm(PasswordChangeForm):
    """
    Extends Django's built-in PasswordChangeForm with crispy layout.
    Validates old password before accepting new one.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Override widget attrs for consistent Tailwind styling
        for field_name in ["old_password", "new_password1", "new_password2"]:
            self.fields[field_name].widget.attrs.update({"class": "form-input"})

        self.helper = _make_helper("Change Password", form_id="change-password-form")
        self.helper.layout = Layout(
            Field("old_password",  css_class="form-input"),
            Field("new_password1", css_class="form-input"),
            Field("new_password2", css_class="form-input"),
        )