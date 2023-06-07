"""
stripe app URLS
"""

from django.urls import path

from commerce_coordinator.apps.stripe.views import WebhookView

app_name = 'stripe'
urlpatterns = [
    path('webhook/', WebhookView.as_view(), name='stripe_webhook'),
]
