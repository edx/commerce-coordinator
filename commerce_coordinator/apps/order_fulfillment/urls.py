"""
order_fulfillment app URLS
"""

from django.urls import path

from commerce_coordinator.apps.order_fulfillment.views import OrderFulfillmentCompletionStatusWebhookView

app_name = 'order_fulfillment'
urlpatterns = [
    path(
        'fulfillment-response-webhook/',
        OrderFulfillmentCompletionStatusWebhookView.as_view(),
        name='fulfillment_response_webhook'
    ),
]
