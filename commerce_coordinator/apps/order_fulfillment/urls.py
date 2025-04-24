"""
order_fulfillment app URLS
"""

from django.urls import path

from commerce_coordinator.apps.order_fulfillment.views import FulfillOrderWebhookView

app_name = 'order_fulfillment'
urlpatterns = [
    path('fulfill-order/', FulfillOrderWebhookView.as_view(), name='fulfill_order_webhook'),
]
