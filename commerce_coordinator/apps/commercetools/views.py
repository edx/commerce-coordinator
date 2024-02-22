"""
Views for the commercetools app
"""
import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from commerce_coordinator.apps.commercetools.serializers import OrderFulfillViewInputSerializer
from commerce_coordinator.apps.commercetools.signals import fulfill_order_placed_signal

from .catalog_info.edx_utils import get_edx_items, get_edx_lms_user_id, get_edx_product_course_run_key, is_edx_lms_order
from .clients import CommercetoolsAPIClient
from .serializers import OrderFulfillMessageInputSerializer
from .utils import (
    extract_ct_order_information_for_braze_canvas,
    extract_ct_product_information_for_braze_canvas,
    send_order_confirmation_email
)

logger = logging.getLogger(__name__)
SOURCE_SYSTEM = 'commercetools'


class OrderFulfillView(APIView):
    """Order Fulfillment View"""

    def post(self, request):
        """Receive a message from commerce tools forwarded by aws event bridge"""
        input_data = {
            **request.data
        }

        logger.debug('[CT-OrderFulfillView] Message received from commercetools with details: %s', input_data)

        message_details = OrderFulfillMessageInputSerializer(data=input_data)
        message_details.is_valid(raise_exception=True)

        client = CommercetoolsAPIClient()
        order_id = message_details.data['order_id']
        order = client.get_order_by_id(order_id)
        customer = client.get_customer_by_id(order.customer_id)

        if not (customer and order and is_edx_lms_order(order)):
            logger.debug('[CT-OrderFulfillView] order %s is not an edX order', order_id)

            return Response(status=status.HTTP_200_OK)

        logger.debug('[CT-OrderFulfillView] processing edX order %s', order_id)

        lms_user_id = get_edx_lms_user_id(customer)

        default_params = {
            'email_opt_in': True,  # ?? Where?
            'order_number': order.id,
            'provider_id': None,
            'edx_lms_user_id': lms_user_id,
            'course_mode': 'verified',
            'date_placed': order.last_modified_at.strftime('%b %d, %Y'),
            'source_system': SOURCE_SYSTEM,
        }
        canvas_entry_properties = {"products": []}
        canvas_entry_properties.update(extract_ct_order_information_for_braze_canvas(customer, order))

        for item in get_edx_items(order):
            logger.debug('[CT-OrderFulfillView] processing edX order %s, line item %s', order_id, item.variant.sku)

            serializer = OrderFulfillViewInputSerializer(data={
                **default_params,
                'course_id': get_edx_product_course_run_key(item),  # likely not correct
            })

            if serializer.is_valid(raise_exception=True):  # pragma no cover
                payload = serializer.validated_data
                fulfill_order_placed_signal.send_robust(
                    sender=self.__class__,
                    **payload
                )
                product_information = extract_ct_product_information_for_braze_canvas(item)
                canvas_entry_properties["products"].append(product_information)
        send_order_confirmation_email(lms_user_id, customer.email, canvas_entry_properties)

        return Response(status=status.HTTP_200_OK)
