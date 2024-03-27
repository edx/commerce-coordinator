"""
Views for the commercetools app
"""
import logging

from commercetools import CommercetoolsError
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from commerce_coordinator.apps.commercetools.catalog_info.constants import TwoUKeys
from commerce_coordinator.apps.commercetools.serializers import OrderFulfillViewInputSerializer
from commerce_coordinator.apps.commercetools.signals import fulfill_order_placed_signal
from commerce_coordinator.apps.core.segment import track

from .authentication import JwtBearerAuthentication
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

    authentication_classes = [JwtBearerAuthentication, SessionAuthentication]
    permission_classes = [IsAdminUser]

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

    authentication_classes = [JwtBearerAuthentication, SessionAuthentication]
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
    """View to refund an order's line item."""

    authentication_classes = [JwtBearerAuthentication, SessionAuthentication]
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
        lms_user_id = get_edx_lms_user_id(customer)

        logger.debug('[CT-OrderReturnedView] calling stripe to refund payment intent %s', payment_intent_id)
        # TODO: Return payment if payment intent id is set

        segment_event_properties = self._prepare_segment_event_properties(order)  # pragma no cover

        for line_item in get_edx_items(order):
            course_run = get_edx_product_course_run_key(line_item)

            # TODO: Remove LMS Enrollment
            logger.debug(
                '[CT-OrderSanctionedView] calling lms to unenroll user %s in %s',
                lms_user_name, course_run
            )

            product = {
                'product_id': line_item.product_key,
                'sku': line_item.variant.sku if hasattr(line_item.variant, 'sku') else None,
                'name': line_item.name['en-US'],
                'price': self._cents_to_dollars(line_item.price.value),
                'quantity': line_item.quantity,
                'category': self._get_line_item_attribute(line_item, 'primarySubjectArea'),
                'image_url': line_item.variant.images[0].url if line_item.variant.images else None,
                'brand': self._get_line_item_attribute(line_item, 'brand-text')
            }
            segment_event_properties['products'].append(product)

        if segment_event_properties['products']:  # pragma no cover
            # Emitting the 'Order Refunded' Segment event upon successfully processing a refund.
            track(
                lms_user_id=lms_user_id,
                event='Order Refunded',
                properties=segment_event_properties
            )

        return Response(status=status.HTTP_200_OK)

    @staticmethod
    def _get_line_item_attribute(line_item, attribute_name):  # pragma no cover
        """Utility to get line item's attribute's value."""
        attribute_value = None
        for attribute in line_item.variant.attributes:
            if attribute.name == attribute_name and hasattr(attribute, 'value'):
                if isinstance(attribute.value, dict):
                    attribute_value = attribute.value.get('label', None)
                elif isinstance(attribute.value, str):
                    attribute_value = attribute.value
                break

        return attribute_value

    @staticmethod
    def _cents_to_dollars(amount):
        return amount.cent_amount / pow(
            10, amount.fraction_digits
            if hasattr(amount, 'fraction_digits')
            else 2
        )

    def _prepare_segment_event_properties(self, order):  # pragma no cover
        return {
            'track_plan_id': 19,
            'trigger_source': 'server-side',
            'order_id': order.id,
            'checkout_id': order.cart.id,
            'return_id': '',  # TODO: [https://2u-internal.atlassian.net/browse/SONIC-391] Set CT return ID here.
            'total': self._cents_to_dollars(order.taxed_price.total_gross),
            'currency': order.taxed_price.total_gross.currency_code,
            'tax': self._cents_to_dollars(order.taxed_price.total_tax),
            'coupon': order.discount_codes[-1].discount_code.obj.code if order.discount_codes else None,
            'coupon_name': [discount.discount_code.obj.code for discount in order.discount_codes[:-1]],
            'discount': self._cents_to_dollars(
                order.discount_on_total_price.discounted_amount) if order.discount_on_total_price else 0,
            'title': get_edx_items(order)[0].name['en-US'] if get_edx_items(order) else None,
            'products': []
        }
