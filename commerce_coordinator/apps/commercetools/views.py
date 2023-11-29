"""
Views for the commercetools app
"""
import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import OrderFulfillMessageInputSerializer

logger = logging.getLogger(__name__)


class OrderFulfillView(APIView):
    """Order Fulfillment View"""

    def post(self, request):
        """Receive a message from commerce tools forwarded by aws event bridge"""
        input_data = {
            **request.data
        }
        message_details = OrderFulfillMessageInputSerializer(data=input_data)
        message_details.is_valid(raise_exception=True)
        logger.debug('[OrderFulfillView] Message received from commercetools with details: %s', message_details.data)

        # TODO: Use the commerce tools sdk to get the information about the order
        # using the order_id received in the message to trigger fulfillment

        return Response(status=status.HTTP_200_OK)
