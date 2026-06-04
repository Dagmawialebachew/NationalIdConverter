from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views.generic import FormView, TemplateView
from django.contrib import messages
from django.urls import reverse_lazy
from .forms import ReceiptSubmissionForm
from .models import PLAN_TIERS

class SubmitPaymentProofView(LoginRequiredMixin, FormView):
    template_name = "billing/submit_proof.html"
    form_class = ReceiptSubmissionForm
    success_url = reverse_lazy('billing:success_status')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        plan_slug = self.kwargs.get('plan_slug')
        
        # Hardcoded dictionary fallback matching your pricing grid prices
        PLAN_PRICES = {
            'starter': '25',
            'plus': '50',
            'basic': '275',
            'standard': '800',
            'printing-pro': '3,450',
            'enterprise': '17,200',
        }
        
        context['plan_slug'] = plan_slug
        context['price'] = PLAN_PRICES.get(plan_slug, '0')
        return context

    def form_valid(self, form):
        plan_slug = self.kwargs.get('plan_slug')
        # Associate instance to verified custom authenticated user directly
        form.instance.user = self.request.user
        form.instance.plan_tier = plan_slug
        form.save()
        messages.success(self.request, "Your payment proof was uploaded successfully! Our staff will verify it shortly.")
        return super().form_valid(form)

class PaymentSuccessStatusView(LoginRequiredMixin, TemplateView):
    template_name = "billing/success_status.html"