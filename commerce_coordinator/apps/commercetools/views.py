"""
Views for the commercetools app
"""
import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from commerce_coordinator.apps.core.models import User
from commerce_coordinator.apps.core.signal_helpers import format_signal_results
from commerce_coordinator.apps.ecommerce.serializers import OrderFulfillViewInputSerializer
from commerce_coordinator.apps.ecommerce.signals import fulfill_order_placed_signal

from .catalog_info.constants import DEFAULT_ORDER_EXPANSION
from .catalog_info.edx_utils import (
    get_edx_items,
    get_edx_lms_user_id,
    get_edx_lms_user_name,
    get_edx_product_course_run_key,
    is_edx_lms_order
)
from .clients import CommercetoolsAPIClient
from .serializers import OrderFulfillMessageInputSerializer

logger = logging.getLogger(__name__)


class OrderFulfillView(APIView):
    """Order Fulfillment View"""

    def post(self, request):
        """Receive a message from commerce tools forwarded by aws event bridge"""
        input_data = {
            **request.data
        }

        logger.debug('[OrderFulfillView] Message received from commercetools with details: %s', input_data)

        message_details = OrderFulfillMessageInputSerializer(data=input_data)
        message_details.is_valid(raise_exception=True)

        client = CommercetoolsAPIClient()
        order_id = message_details.detail.orderId
        order = client.get_order_by_id(order_id)
        customer = client.get_customer_by_id(order.customer_id)

        lms_user_id = get_edx_lms_user_id(customer)

        default_params = {
            'email_opt_in': True,  # ?? Where?
            'order_number': order.order_number or order.id,
            'provider_id': None,
            'user': get_edx_lms_user_name(customer),
            'course_mode': 'verified',
            'date_placed': (order.completed_at or order.last_modified_at).timestamp(),
        }

        if customer and order and is_edx_lms_order(order):
            logger.debug('[OrderFulfillView] processing edX order %s', order_id)
            items = get_edx_items(order)

            for item in items:
                serializer = OrderFulfillViewInputSerializer(data={
                    **default_params,
                    'course_id': get_edx_product_course_run_key(item),  # likely not correct
                })

                if serializer.is_valid(raise_exception=True):
                    payload = serializer.validated_data

                    payload['edx_lms_user_id'] = lms_user_id
                    payload.pop('user')

                    results = fulfill_order_placed_signal.send_robust(
                        sender=self.__class__,
                        **payload
                    )

                    return Response(format_signal_results(results), status=status.HTTP_200_OK)
        else:
            logger.debug('[OrderFulfillView] order %s is not an edX order', order_id)

        return Response(status=status.HTTP_200_OK)
