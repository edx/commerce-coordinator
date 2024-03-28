"""
Views for the commercetools app
"""
import logging

from edx_django_utils.cache import TieredCache
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from commerce_coordinator.apps.commercetools.authentication import JwtBearerAuthentication
from commerce_coordinator.apps.commercetools.constants import SOURCE_SYSTEM
from commerce_coordinator.apps.commercetools.serializers import OrderMessageInputSerializer
from commerce_coordinator.apps.commercetools.sub_messages.signals_dispatch import (
    fulfill_order_placed_message_signal,
    fulfill_order_returned_signal,
    fulfill_order_sanctioned_message_signal
)
from commerce_coordinator.apps.core.memcache import safe_key

logger = logging.getLogger(__name__)


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

        fulfill_order_placed_message_signal.send_robust(
            sender=self,
            order_id=order_id,
            source_system=SOURCE_SYSTEM
        )

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

        fulfill_order_sanctioned_message_signal.send_robust(
            sender=self,
            order_id=order_id,
        )

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

        fulfill_order_returned_signal.send_robust(
            sender=self,
            order_id=order_id,
        )

        return Response(status=status.HTTP_200_OK)
