"""
Views for the commercetools app
"""
import logging

from commercetools import CommercetoolsError
from edx_django_utils.cache import TieredCache
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from commerce_coordinator.apps.commercetools.authentication import JwtBearerAuthentication
from commerce_coordinator.apps.commercetools.catalog_info.constants import TwoUKeys
from commerce_coordinator.apps.commercetools.catalog_info.edx_utils import (
    get_edx_is_sanctioned,
    get_edx_items,
    get_edx_lms_user_id,
    get_edx_lms_user_name,
    get_edx_order_workflow_state_key,
    get_edx_payment_intent_id,
    get_edx_product_course_run_key,
    is_edx_lms_order
)
from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient
from commerce_coordinator.apps.commercetools.serializers import (
    OrderFulfillViewInputSerializer,
    OrderMessageInputSerializer
)
from commerce_coordinator.apps.commercetools.signals import fulfill_order_placed_signal
from commerce_coordinator.apps.commercetools.utils import (
    extract_ct_order_information_for_braze_canvas,
    extract_ct_product_information_for_braze_canvas,
    send_order_confirmation_email
)
from commerce_coordinator.apps.core.memcache import safe_key

logger = logging.getLogger(__name__)

SOURCE_SYSTEM = 'commercetools'

NOTIFICATION_CACHE_TTL_SECS = 60 * 10  # 10 Mins


class SingleInvocationAPIView(APIView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.meta_id = None
        self.meta_view = None
        self.meta_should_mark_not_running = True

    @staticmethod
    def _view_cache_key(view: str, identifier: str) -> str:
        return safe_key(key=f"{view}_{identifier}", key_prefix="ct_sub_msg_invo", version="1")

    @staticmethod
    def _mark_running(view: str, identifier: str, tf=True):
        key = SingleInvocationAPIView._view_cache_key(view, identifier)

        if TieredCache.get_cached_response(key).is_found or not tf:
            try:
                TieredCache.delete_all_tiers(key)

            # not all caches throw this but a few do.
            except ValueError as _:  # pragma no cover
                # No-Op, Key not found.
                pass

        if tf:
            TieredCache.set_all_tiers(key, tf, NOTIFICATION_CACHE_TTL_SECS)

    @staticmethod
    def _is_running(view: str, identifier: str):
        key = SingleInvocationAPIView._view_cache_key(view, identifier)
        cache_value = TieredCache.get_cached_response(key)
        if cache_value.is_found or cache_value.get_value_or_default(False):
            logger.debug(f'[CT-{view}] Currently processing request for %s, ignoring invocation', identifier)
            return True
        return False

    def set_view(self, view: str):
        self.meta_view = view

    def set_identifier(self, identifier: str):
        self.meta_id = identifier

    def finalize_response(self, request, response, *args, **kwargs):
        tag = self.meta_view
        identifier = self.meta_id
        if self.meta_should_mark_not_running:
            SingleInvocationAPIView._mark_running(tag, identifier, False)
        return super().finalize_response(request, response, *args, **kwargs)

    def handle_exception(self, exc):
        tag = self.meta_view
        identifier = self.meta_id
        SingleInvocationAPIView._mark_running(tag, identifier, False)
        return super().handle_exception(exc)


# noinspection DuplicatedCode
class OrderFulfillView(SingleInvocationAPIView):
    """Order Fulfillment View"""

    authentication_classes = [JwtBearerAuthentication, SessionAuthentication]
    permission_classes = [IsAdminUser]

    def post(self, request):
        """Receive a message from commerce tools forwarded by aws event bridge"""

        tag = type(self).__name__

        input_data = {
            **request.data
        }

        logger.debug(f'[CT-{tag}] Message received from commercetools with details: %s', input_data)

        message_details = OrderMessageInputSerializer(data=input_data)
        message_details.is_valid(raise_exception=True)

        order_id = message_details.data['order_id']

        if self._is_running(tag, order_id):
            self.meta_should_mark_not_running = False
            return Response(status=status.HTTP_200_OK)
        else:
            self._mark_running(tag, order_id)

        # TODO: GRM Make in to tasks

        client = CommercetoolsAPIClient()

        try:
            order = client.get_order_by_id(order_id)
        except CommercetoolsError as err:  # pragma no cover
            logger.error(f'[CT-{tag}] Order not found: {order_id} with CT error {err}, {err.errors}')
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            customer = client.get_customer_by_id(order.customer_id)
        except CommercetoolsError as err:  # pragma no cover
            logger.error(f'[CT-{tag}]  Customer not found: {order.customer_id} for order {order_id} with '
                         f'CT error {err}, {err.errors}')
            return Response(status=status.HTTP_404_NOT_FOUND)

        if not (customer and order and is_edx_lms_order(order)):
            logger.debug(f'[CT-{tag}] order %s is not an edX order', order_id)

            return Response(status=status.HTTP_200_OK)

        logger.debug(f'[CT-{tag}] processing edX order %s', order_id)

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
            logger.debug(f'[CT-{tag}] processing edX order %s, line item %s', order_id, item.variant.sku)

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
class OrderSanctionedView(SingleInvocationAPIView):
    """View to sanction an order and deactivate the lms user"""

    authentication_classes = [JwtBearerAuthentication, SessionAuthentication]
    permission_classes = [IsAdminUser]

    def post(self, request):
        """
        Receive a message from commerce tools forwarded by aws event bridge
        to sanction order and deactivate user through LMS
        """
        tag = type(self).__name__

        input_data = {
            **request.data
        }

        logger.debug(f'[CT-{tag}] Message received from commercetools with details: %s', input_data)

        message_details = OrderMessageInputSerializer(data=input_data)
        message_details.is_valid(raise_exception=True)

        order_id = message_details.data['order_id']

        if self._is_running(tag, order_id):
            self.meta_should_mark_not_running = False
            return Response(status=status.HTTP_200_OK)
        else:
            self._mark_running(tag, order_id)

        # TODO: GRM Make in to tasks

        client = CommercetoolsAPIClient()
        try:
            order = client.get_order_by_id(order_id)
        except CommercetoolsError as err:  # pragma no cover
            logger.error(f'[CT-{tag}] Order not found: {order_id} with CT error {err}, {err.errors}')
            return Response(status=status.HTTP_404_NOT_FOUND)

        order_workflow_state = get_edx_order_workflow_state_key(order)
        if not order_workflow_state:
            logger.debug(f'[CT-{tag}] order %s has no workflow/transition state', order_id)

        try:
            customer = client.get_customer_by_id(order.customer_id)
        except CommercetoolsError as err:  # pragma no cover
            logger.error(f'[CT-{tag}]  Customer not found: {order.customer_id} for order {order_id} with '
                         f'CT error {err}, {err.errors}')
            return Response(status=status.HTTP_404_NOT_FOUND)

        if not (customer and order and is_edx_lms_order(order)):
            logger.debug(f'[CT-{tag}] order %s is not an edX order', order_id)
            return Response(status=status.HTTP_200_OK)

        if get_edx_is_sanctioned(order):
            logger.debug(
                f'[CT-{tag}] order state for order %s is not %s. Actual value is %s',
                order_id,
                TwoUKeys.SDN_SANCTIONED_ORDER_STATE,
                order_workflow_state
            )

            lms_user_name = get_edx_lms_user_name(customer)
            logger.debug(f'[CT-{tag}] calling lms to deactivate user %s', lms_user_name)

            # TODO: SONIC-155 use lms_user_name to call LMS endpoint to deactivate user

        return Response(status=status.HTTP_200_OK)


# noinspection DuplicatedCode
class OrderReturnedView(SingleInvocationAPIView):
    """View to sanction an order and deactivate the lms user"""

    authentication_classes = [JwtBearerAuthentication, SessionAuthentication]
    permission_classes = [IsAdminUser]

    def post(self, request):
        """
        Receive a message from commerce tools forwarded by aws event bridge
        to sanction order and deactivate user through LMS
        """

        tag = type(self).__name__

        input_data = {
            **request.data
        }

        logger.debug(f'[CT-{tag}] Message received from commercetools with details: %s', input_data)

        message_details = OrderMessageInputSerializer(data=input_data)
        message_details.is_valid(raise_exception=True)

        order_id = message_details.data['order_id']

        if self._is_running(tag, order_id):
            self.meta_should_mark_not_running = False
            return Response(status=status.HTTP_200_OK)
        else:
            self._mark_running(tag, order_id)

        # TODO: GRM Make in to tasks

        client = CommercetoolsAPIClient()

        try:
            order = client.get_order_by_id(order_id)
        except CommercetoolsError as err:  # pragma no cover
            logger.error(f'[CT-{tag}] Order not found: {order_id} with CT error {err}, {err.errors}')
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            customer = client.get_customer_by_id(order.customer_id)
        except CommercetoolsError as err:  # pragma no cover
            logger.error(f'[CT-{tag}]  Customer not found: {order.customer_id} for order {order_id} with '
                         f'CT error {err}, {err.errors}')
            return Response(status=status.HTTP_404_NOT_FOUND)

        if not (customer and order and is_edx_lms_order(order)):
            logger.debug(f'[CT-{tag}] order %s is not an edX order', order_id)
            return Response(status=status.HTTP_200_OK)

        payment_intent_id = get_edx_payment_intent_id(order)
        lms_user_name = get_edx_lms_user_name(customer)

        logger.debug(f'[CT-{tag}] calling stripe to refund payment intent %s', payment_intent_id)

        # TODO: Return payment if payment intent id is set

        for line_item in get_edx_items(order):
            course_run = get_edx_product_course_run_key(line_item)

            # TODO: Remove LMS Enrollment
            logger.debug(
                f'[CT-{tag}] calling lms to unenroll user %s in %s',
                lms_user_name, course_run
            )

        return Response(status=status.HTTP_200_OK)
