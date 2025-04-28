"""
order_fulfillment app URLS
"""

from django.urls import path

from commerce_coordinator.apps.order_fulfillment.views import FulfillmentResponseWebhookView

app_name = 'order_fulfillment'
urlpatterns = [
    path(
        'fulfillment-response-webhook/',
        FulfillmentResponseWebhookView.as_view(),
        name='fulfillment_response_webhook'
    ),
]
