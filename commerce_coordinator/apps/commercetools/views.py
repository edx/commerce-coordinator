"""
Views for the commercetools app
"""
import logging

from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from commerce_coordinator.apps.commercetools.authentication import JwtBearerAuthentication
from commerce_coordinator.apps.commercetools.constants import SOURCE_SYSTEM
from commerce_coordinator.apps.commercetools.serializers import (
    OrderLineItemMessageInputSerializer,
    OrderReturnedViewMessageInputSerializer,
    OrderSanctionedViewMessageInputSerializer
)
from commerce_coordinator.apps.commercetools.sub_messages.signals_dispatch import (
    fulfill_order_placed_message_signal,
    fulfill_order_returned_signal,
    fulfill_order_sanctioned_message_signal
)
from commerce_coordinator.apps.core.memcache import safe_key
from commerce_coordinator.apps.core.tasks import acquire_task_lock
from commerce_coordinator.apps.core.views import SingleInvocationAPIView
from commerce_coordinator.apps.rollout.waffle import is_order_fulfillment_service_forwarding_enabled

logger = logging.getLogger(__name__)


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

        is_order_fulfillment_forwarding_enabled = is_order_fulfillment_service_forwarding_enabled(request)

        logger.info(f'[CT-{tag}] Message received from commercetools with details: {input_data}')

        message_details = OrderLineItemMessageInputSerializer(data=input_data)
        message_details.is_valid(raise_exception=True)

        order_id = message_details.data['order_id']
        line_item_state_id = message_details.data['to_state']['id']
        message_id = message_details.data['message_id']

        task_key = safe_key(key=order_id, key_prefix=tag, version='1')

        if not acquire_task_lock(task_key):
            logger.info(
                f"Task {task_key} is already running. Exiting current task. Order ID: {order_id}."
            )
            return Response(status=status.HTTP_200_OK)

        fulfill_order_placed_message_signal.send_robust(
            sender=self,
            order_id=order_id,
            line_item_state_id=line_item_state_id,
            source_system=SOURCE_SYSTEM,
            message_id=message_id,
            is_order_fulfillment_forwarding_enabled=is_order_fulfillment_forwarding_enabled
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

        logger.info(f'[CT-{tag}] Message received from commercetools with details: {input_data}')

        message_details = OrderSanctionedViewMessageInputSerializer(data=input_data)
        message_details.is_valid(raise_exception=True)

        order_id = message_details.data['order_id']
        message_id = message_details.data['message_id']

        if self._is_running(tag, order_id):  # pragma no cover
            self.meta_should_mark_not_running = False
            return Response(status=status.HTTP_200_OK)
        else:
            self.mark_running(tag, order_id)

        fulfill_order_sanctioned_message_signal.send_robust(
            sender=self,
            order_id=order_id,
            message_id=message_id
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

        logger.info(f'[CT-{tag}] Message received from commercetools with details: {input_data}')

        message_details = OrderReturnedViewMessageInputSerializer(data=input_data)
        message_details.is_valid(raise_exception=True)
        order_id = message_details.data['order_id']

        return_items = message_details.get_return_line_items()
        message_id = message_details.data['message_id']

        fulfill_order_returned_signal.send_robust(
            sender=self,
            order_id=order_id,
            return_items=return_items,
            message_id=message_id
        )

        return Response(status=status.HTTP_200_OK)
