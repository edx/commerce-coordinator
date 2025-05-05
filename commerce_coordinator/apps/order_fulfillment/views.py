"""
Views for the order fulfillment app
"""
import logging

from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from commerce_coordinator.apps.core.views import SingleInvocationAPIView
from commerce_coordinator.apps.lms.clients import FulfillmentType
from commerce_coordinator.apps.lms.signals import fulfillment_completed_update_ct_line_item_signal
from commerce_coordinator.apps.order_fulfillment.serializers import FulfillOrderWebhookSerializer
from commerce_coordinator.apps.order_fulfillment.aws_event_bridge_utils.aws_eb_api_key_authentication import (
    AWSAPIKeyAuthentication
)

logger = logging.getLogger(__name__)


class FulfillmentResponseWebhookView(SingleInvocationAPIView):
    """
    Endpoint for Order Fulfillment webhook Response. This endpoint receives fulfillment
    response from fulfillment providers and updates CT order object with response data.
    """
    http_method_names = ['post']
    authentication_classes = [AWSAPIKeyAuthentication]
    permission_classes = [AllowAny]

    @csrf_exempt
    def post(self, request):
        """Webhook entry point for order fulfillment response."""
        tag = type(self).__name__

        logger.info(f'[CT-{tag}] Message received from order-fulfillment with details: {request.data}')

        try:
            input_data = {
                **request.data.get('detail')
            }

            validator = FulfillOrderWebhookSerializer(data=input_data)
            validator.is_valid(raise_exception=True)
            validated_data = validator.validated_data

            fulfillment_type = validated_data.get('fulfillment_type')
            if fulfillment_type == FulfillmentType.ENTITLEMENT.value:
                entitlement_uuid = validated_data.get('entitlement_uuid', None)
                if not entitlement_uuid:
                    raise ValidationError('Entitlement uuid is required for Entitlement Fulfillment.')

            fulfillment_completed_update_ct_line_item_signal.send_robust(
                sender=self.__class__,
                **validated_data
            )

            return Response(
                {'message': 'Order Fulfillment Response event processed successfully.'},
                status=status.HTTP_200_OK
            )
        except Exception as exc:
            logger.error(f"[CT-{tag}] Error in FulfillmentResponseWebhookView while processing request: {exc}")
            return Response(status=status.HTTP_400_BAD_REQUEST)
