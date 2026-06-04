# apps/accounts/adapters.py
import logging
import dns.resolver  # Installed via dnspython
from allauth.account.adapter import DefaultAccountAdapter
from django.forms import ValidationError
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()

class AntiExploitAccountAdapter(DefaultAccountAdapter):
    """
    Custom Allauth Adapter that verifies email structural validity, 
    eliminates sub-addressing exploits, and checks if mail servers exist.
    """

    def clean_email(self, email):
        # 1. Standardize and clean input
        email = super().clean_email(email).lower().strip()
        
        try:
            local_part, domain = email.split('@', 1)
        except ValueError:
            raise ValidationError("Please enter a valid email address.")

        # 2. INSTANT LIVE DNS VERIFICATION (Prevents completely fake/non-existent emails)
        try:
            # Query DNS to check if the domain has active Mail Exchanger (MX) records
            dns.resolver.resolve(domain, 'MX')
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, Exception):
            # Fallback check: check if domain resolves to an IP address at all
            try:
                dns.resolver.resolve(domain, 'A')
            except Exception:
                logger.warning(f"Registration Blocked: Non-existent domain @{domain}")
                raise ValidationError(
                    f"The domain @{domain} does not appear to exist or cannot receive emails."
                )

        # 3. Apply strict processing rules for Google Mail identities (Gmail Tricks)
        if domain in ['gmail.com', 'googlemail.com']:
            local_part = local_part.split('+', 1)[0]
            local_part = local_part.replace('.', '')
            normalized_email = f"{local_part}@{domain}"
            
            # Uniqueness check against structural variations
            if User.objects.filter(email=normalized_email).exists():
                raise ValidationError("An account is already registered under this email variation.")
            
            return normalized_email

        return email