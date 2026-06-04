import base64
from django import forms
from django.core.exceptions import ValidationError
from .models import PaymentVerification

ALLOWED_RECEIPT_TYPES = ['image/jpeg', 'image/png', 'image/jpg']
MAX_RECEIPT_SIZE = 5 * 1024 * 1024  # 5MB

class ReceiptSubmissionForm(forms.ModelForm):
    # Made completely optional so users don't have to fill it out
    transaction_reference = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input'})
    )
    
    receipt_file = forms.ImageField(
        required=True,
        help_text="Upload a screenshot of your Telebirr, CBE Birr or Mobile Banking transaction."
    )

    class Meta:
        model = PaymentVerification
        fields = ['transaction_reference', 'receipt_file']

    def clean_receipt_file(self):
        file = self.cleaned_data.get('receipt_file')
        if file:
            if file.size > MAX_RECEIPT_SIZE:
                raise ValidationError("The receipt file size cannot exceed 5MB.")
            if file.content_type not in ALLOWED_RECEIPT_TYPES:
                raise ValidationError("Only JPEG, JPG, and PNG images are supported.")
            
            try:
                file_bytes = file.read()
                base64_encoded = base64.b64encode(file_bytes).decode('utf-8')
                return f"data:{file.content_type};base64,{base64_encoded}"
            except Exception:
                raise ValidationError("Could not read valid image bytes from submission sample.")
        return file
    
    def clean_transaction_reference(self):
        ref = self.cleaned_data.get('transaction_reference')
        # If the reference is empty or just whitespace, return None instead of an empty string
        return ref.strip() if ref and ref.strip() else None

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.receipt_image_base64 = self.cleaned_data.get('receipt_file')
        if commit:
            instance.save()
        return instance