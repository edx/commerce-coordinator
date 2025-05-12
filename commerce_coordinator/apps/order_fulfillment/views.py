"""
Views for the order fulfillment app
"""
import logging

from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from commerce_coordinator.apps.commercetools.authentication import JwtBearerAuthentication
from commerce_coordinator.apps.core.views import SingleInvocationAPIView
from commerce_coordinator.apps.lms.clients import FulfillmentType
from commerce_coordinator.apps.lms.signals import fulfillment_completed_update_ct_line_item_signal
from commerce_coordinator.apps.order_fulfillment.serializers import FulfillOrderWebhookSerializer

logger = logging.getLogger(__name__)


class OrderFulfillmentCompletionStatusWebhookView(SingleInvocationAPIView):
    """
    Endpoint for Order Fulfillment webhook Response. This endpoint receives fulfillment
    response from fulfillment providers and updates CT order object with response data.
    """
    http_method_names = ['post']
    authentication_classes = [JwtBearerAuthentication, SessionAuthentication]
    permission_classes = [IsAdminUser]

    @csrf_exempt
    def post(self, request):
        """Webhook entry point for order fulfillment response."""
        tag = type(self).__name__

        input_data = {
            **request.data.get('detail', None)
        }

        logger.info(f'[CT-{tag}] Message received from order-fulfillment with details: {input_data}')

        validator = FulfillOrderWebhookSerializer(data=input_data)
        validator.is_valid(raise_exception=True)
        validated_data = validator.validated_data

        fulfillment_type = validated_data.get('fulfillment_type')
        is_fulfilled = validated_data.get('is_fulfilled')
        if is_fulfilled and fulfillment_type == FulfillmentType.ENTITLEMENT.value:
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
