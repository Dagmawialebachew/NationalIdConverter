from django.contrib import admin, messages
from django.utils.safestring import mark_safe
from .models import PaymentVerification

@admin.register(PaymentVerification)
class PaymentVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan_tier', 'transaction_reference', 'status', 'created_at')
    list_filter = ('status', 'plan_tier')
    search_fields = ('user__email', 'transaction_reference')
    readonly_fields = ('receipt_image_preview',)
    actions = ['approve_payments_bulk']

    def receipt_image_preview(self, instance):
        if instance.receipt_image_base64:
            return mark_safe(f'<img src="{instance.receipt_image_base64}" style="max-width: 450px; height:auto; border-radius:8px;" />')
        return "No image string data captured."

    @admin.action(description="Approve selected receipts and allocate credits")
    def approve_payments_bulk(self, request, queryset):
        """
        Allows staff to verify rows directly from the table checkbox view.
        Looping explicitly ensures individual model save() lifecycles execute cleanly.
        """
        count = 0
        for verification in queryset:
            if verification.status != 'approved':
                verification.status = 'approved'
                verification.save() # Invokes our robust model-level transition engine
                count += 1
        
        self.message_user(
            request, 
            f"Successfully approved {count} receipt entries and provisioned plan tier balances.", 
            messages.SUCCESS
        )