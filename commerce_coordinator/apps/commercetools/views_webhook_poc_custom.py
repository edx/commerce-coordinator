"""
Views for the commercetools app
"""
import logging
from django.http import JsonResponse
from rest_framework import status
from rest_framework.response import Response

from commerce_coordinator.apps.commercetools.fulfillment_webhook.webhook_authentication import \
    HMACSignatureWebhookAuthentication
from commerce_coordinator.apps.commercetools.fulfillment_webhook.webhook_caller import HMACWebhookCaller
from commerce_coordinator.apps.core.views import SingleInvocationAPIView

logger = logging.getLogger(__name__)

class TriggerOrderFulfillmentCustom(SingleInvocationAPIView):
    """Order Fulfillment View"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.webhook_client = HMACWebhookCaller()

    def get(self, request):
        """Receive a message from commercetools forwarded by aws event bridge"""

        tag = type(self).__name__

        logger.info(f'[CT-{tag}] Message received to trigger fulfillment - Custom.')

        url = 'http://localhost:8155/fulfill-custom/'
        payload = {
            "order_id": "1234",
        }
        response = self.webhook_client.call(url, payload)

        if response and response.status_code == 200:
            logger.info(f"[CT-{tag}] Custom Webhook call done. Response: {response.status_code} - {response.text}")
            return Response(status=status.HTTP_200_OK)
        else:
            logger.warning(f"[CT-{tag}] Custom Webhook call failed.")
            return Response(status=status.HTTP_503_SERVICE_UNAVAILABLE)


class OrderFulfillmentResponseCustom(SingleInvocationAPIView):
    """Order Fulfillment View"""

    authentication_classes = [HMACSignatureWebhookAuthentication]

    def post(self, request):
        """Receive a message from commercetools forwarded by aws event bridge"""
        print('\n\n\nrequest headers', request.headers)
        is_valid, error_response = self.is_authorized_webhook_request(request)
        if not is_valid:
            return JsonResponse({'error': error_response.get('error')}, status=error_response.get('status'))

        print('\n\n\nrequest data', request.data)

        print('\n\n\n\n Hello, Custom - Order Fulfillment Response received!')
        return Response(status=200)
