"""
frontend_app_payment app URLS
"""

from django.urls import path

from commerce_coordinator.apps.frontend_app_payment.views import (
    DraftPaymentCreateView,
    GetActiveOrderView,
    PaymentGetView
)

app_name = 'frontend_app_payment'
urlpatterns = [
    path('payment', PaymentGetView.as_view(), name='get_payment'),
    path('payment/draft', DraftPaymentCreateView.as_view(), name='create_draft_payment'),
    path('order/active', GetActiveOrderView.as_view(), name='get_active_order'),
]
