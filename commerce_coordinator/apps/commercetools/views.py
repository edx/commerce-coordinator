"""
Views for the commercetools app
"""
import logging

from commercetools import CommercetoolsError
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from commerce_coordinator.apps.commercetools.catalog_info.constants import TwoUKeys
from commerce_coordinator.apps.commercetools.serializers import OrderFulfillViewInputSerializer
from commerce_coordinator.apps.commercetools.signals import fulfill_order_placed_signal

from .catalog_info.edx_utils import (
    get_edx_is_sanctioned,
    get_edx_items,
    get_edx_lms_user_id,
    get_edx_lms_user_name,
    get_edx_order_workflow_state_key,
    get_edx_payment_intent_id,
    get_edx_product_course_run_key,
    is_edx_lms_order
)
from .clients import CommercetoolsAPIClient
from .serializers import OrderMessageInputSerializer
from .utils import (
    extract_ct_order_information_for_braze_canvas,
    extract_ct_product_information_for_braze_canvas,
    send_order_confirmation_email
)

logger = logging.getLogger(__name__)
SOURCE_SYSTEM = 'commercetools'


# noinspection DuplicatedCode
class OrderFulfillView(APIView):
    """Order Fulfillment View"""

    def post(self, request):
        """Receive a message from commerce tools forwarded by aws event bridge"""
        input_data = {
            **request.data
        }

        logger.debug('[CT-OrderFulfillView] Message received from commercetools with details: %s', input_data)

        message_details = OrderMessageInputSerializer(data=input_data)
        message_details.is_valid(raise_exception=True)

        client = CommercetoolsAPIClient()
        order_id = message_details.data['order_id']

        try:
            order = client.get_order_by_id(order_id)
        except CommercetoolsError as err:  # pragma no cover
            logger.error(f'[CT-OrderSanctionedView] Order not found: {order_id} with CT error {err}, {err.errors}')
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            customer = client.get_customer_by_id(order.customer_id)
        except CommercetoolsError as err:  # pragma no cover
            logger.error(f'[CT-OrderFulfillView]  Customer not found: {order.customer_id} for order {order_id} with '
                         f'CT error {err}, {err.errors}')
            return Response(status=status.HTTP_404_NOT_FOUND)

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

            # the following throws and thus doesn't need to be a conditional
            serializer.is_valid(raise_exception=True)  # pragma no cover

            payload = serializer.validated_data
            fulfill_order_placed_signal.send_robust(
                sender=self.__class__,
                **payload
            )
            product_information = extract_ct_product_information_for_braze_canvas(item)
            canvas_entry_properties["products"].append(product_information)
        send_order_confirmation_email(lms_user_id, customer.email, canvas_entry_properties)

        return Response(status=status.HTTP_200_OK)


# noinspection DuplicatedCode
class OrderSanctionedView(APIView):
    """View to sanction an order and deactivate the lms user"""
    permission_classes = [IsAdminUser]

    def post(self, request):
        """
        Receive a message from commerce tools forwarded by aws event bridge
        to sanction order and deactivate user through LMS
        """
        input_data = {
            **request.data
        }

        logger.debug('[CT-OrderSanctionedView] Message received from commercetools with details: %s', input_data)

        message_details = OrderMessageInputSerializer(data=input_data)
        message_details.is_valid(raise_exception=True)

        client = CommercetoolsAPIClient()
        order_id = message_details.data['order_id']

        try:
            order = client.get_order_by_id(order_id)
        except CommercetoolsError as err:  # pragma no cover
            logger.error(f'[CT-OrderSanctionedView] Order not found: {order_id} with CT error {err}, {err.errors}')
            return Response(status=status.HTTP_404_NOT_FOUND)

        order_workflow_state = get_edx_order_workflow_state_key(order)
        if not order_workflow_state:
            logger.debug('[CT-OrderSanctionedView] order %s has no workflow/transition state', order_id)

        try:
            customer = client.get_customer_by_id(order.customer_id)
        except CommercetoolsError as err:  # pragma no cover
            logger.error(f'[CT-OrderSanctionedView]  Customer not found: {order.customer_id} for order {order_id} with '
                         f'CT error {err}, {err.errors}')
            return Response(status=status.HTTP_404_NOT_FOUND)

        if not (customer and order and is_edx_lms_order(order)):
            logger.debug('[CT-OrderSanctionedView] order %s is not an edX order', order_id)
            return Response(status=status.HTTP_200_OK)

        if get_edx_is_sanctioned(order):
            logger.debug(
                '[CT-OrderSanctionedView] order state for order %s is not %s. Actual value is %s',
                order_id,
                TwoUKeys.SDN_SANCTIONED_ORDER_STATE,
                order_workflow_state
            )

            lms_user_name = get_edx_lms_user_name(customer)
            logger.debug('[CT-OrderSanctionedView] calling lms to deactivate user %s', lms_user_name)

            # TODO: SONIC-155 use lms_user_name to call LMS endpoint to deactivate user

        return Response(status=status.HTTP_200_OK)


# noinspection DuplicatedCode
class OrderReturnedView(APIView):
    """View to sanction an order and deactivate the lms user"""
    permission_classes = [IsAdminUser]

    def post(self, request):
        """
        Receive a message from commerce tools forwarded by aws event bridge
        to sanction order and deactivate user through LMS
        """
        input_data = {
            **request.data
        }

        logger.debug('[CT-OrderReturnedView] Message received from commercetools with details: %s', input_data)

        message_details = OrderMessageInputSerializer(data=input_data)
        message_details.is_valid(raise_exception=True)

        client = CommercetoolsAPIClient()
        order_id = message_details.data['order_id']

        try:
            order = client.get_order_by_id(order_id)
        except CommercetoolsError as err:  # pragma no cover
            logger.error(f'[CT-OrderReturnedView] Order not found: {order_id} with CT error {err}, {err.errors}')
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            customer = client.get_customer_by_id(order.customer_id)
        except CommercetoolsError as err:  # pragma no cover
            logger.error(f'[CT-OrderReturnedView]  Customer not found: {order.customer_id} for order {order_id} with '
                         f'CT error {err}, {err.errors}')
            return Response(status=status.HTTP_404_NOT_FOUND)

        if not (customer and order and is_edx_lms_order(order)):
            logger.debug('[CT-OrderReturnedView] order %s is not an edX order', order_id)
            return Response(status=status.HTTP_200_OK)

        payment_intent_id = get_edx_payment_intent_id(order)
        lms_user_name = get_edx_lms_user_name(customer)

        logger.debug('[CT-OrderReturnedView] calling stripe to refund payment intent %s', payment_intent_id)

        # TODO: Return payment if payment intent id is set

        for line_item in get_edx_items(order):
            course_run = get_edx_product_course_run_key(line_item)

            # TODO: Remove LMS Enrollment
            logger.debug(
                '[CT-OrderSanctionedView] calling lms to unenroll user %s in %s',
                lms_user_name, course_run
            )

        return Response(status=status.HTTP_200_OK)
