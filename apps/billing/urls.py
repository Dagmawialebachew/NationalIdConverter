from django.urls import path
from apps.billing import views

app_name = 'billing'

urlpatterns = [
    path('verify/<slug:plan_slug>/', views.SubmitPaymentProofView.as_view(), name='submit_proof'),
    path('status/complete/', views.PaymentSuccessStatusView.as_view(), name='success_status'),
]