"""
frontend_app_payment app URLS
"""

from django.urls import path

from commerce_coordinator.apps.frontend_app_payment.views import (
    GetActiveOrderView,
    PaymentProcessView
)

app_name = 'frontend_app_payment'
urlpatterns = [
    # CC Specific Endpoints
    path('payment/process', PaymentProcessView.as_view(), name='process_payment'),

    # Ecomm IDA Compatible Paths to minimize URL churn in frontend_app_payment
    path('bff/payment/v0/payment/', GetActiveOrderView.as_view(), name='get_active_order'),
]
