"""
Paypal app urls
"""

from django.urls import path

from commerce_coordinator.apps.paypal.views import PayPalWebhookView

app_name = 'paypal'
urlpatterns = [
    path('webhook/', PayPalWebhookView.as_view(), name='paypal_webhook'),
]
