"""
frontend_app_payment app URLS
"""

from django.urls import path

from commerce_coordinator.apps.frontend_app_payment.views import PaymentProcessView

app_name = 'frontend_app_payment'
urlpatterns = [
    # CC Specific Endpoints
    path('payment/process', PaymentProcessView.as_view(), name='process_payment'),
]
