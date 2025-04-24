"""
Views for the order fulfillment app
"""
import logging

from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from commerce_coordinator.apps.core.views import SingleInvocationAPIView
from commerce_coordinator.apps.lms.clients import FulfillmentType
from commerce_coordinator.apps.lms.signals import fulfillment_completed_update_ct_line_item_signal
from commerce_coordinator.apps.order_fulfillment.serializers import FulfillOrderWebhookSerializer

logger = logging.getLogger(__name__)


class FulfillOrderWebhookView(SingleInvocationAPIView):
    """
    Endpoint for Order Fulfillment webhook events. This endpoint receives fulfillment
    updates from fulfillment providers and processes them accordingly.
    """
    http_method_names = ['post']
    authentication_classes = []
    permission_classes = [AllowAny]

    @csrf_exempt
    def post(self, request):
        """Webhook entry point for order fulfillment events."""
        try:
            validator = FulfillOrderWebhookSerializer(data=request.data)
            validator.is_valid(raise_exception=True)
            validated_data = validator.validated_data

            entitlement_uuid = validated_data.get('entitlement_uuid')
            fulfillment_type = validated_data.get('fulfillment_type')

            payload = {
                **validated_data,
                'is_fulfilled': True
            }

            if fulfillment_type == FulfillmentType.ENTITLEMENT.value:
                payload['entitlement_uuid'] = entitlement_uuid

            fulfillment_completed_update_ct_line_item_signal.send_robust(
                sender=self.__class__,
                **payload
            )

            return Response(
                {'message': 'Fulfillment event processed successfully'},
                status=status.HTTP_200_OK
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            log_message = (
                f"[FulfillOrderWebhookView] Error processing fulfill order webhook: {exc} "
                f"with body: {request.data}"
            )
            logger.exception(log_message)

            payload = {
                **validated_data,
                'is_fulfilled': False
            }

            fulfillment_completed_update_ct_line_item_signal.send_robust(
                sender=self.__class__,
                **payload
            )
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
