"""
Views for the titan app
"""

import logging

from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from commerce_coordinator.apps.core.signal_helpers import format_signal_results

from .serializers import OrderFulfillViewInputSerializer
from .signals import fulfill_order_placed_signal

logger = logging.getLogger(__name__)


class OrderFulfillView(APIView):
    """
    API for order fulfillment that is called from Titan.
    """
    parser_classes = [JSONParser]
    permission_classes = [IsAdminUser]

    def post(self, request):
        """
        POST request handler for /fulfill

        Requires a JSON object of the following format:

        .. code-block:: json

            {
                "course_id": "course-v1:edX+DemoX+Demo_Course",
                "course_mode": "verified",
                "order_placed": 1681738233,
                "edx_lms_user_id": 4,
                "email_opt_in": 0,
                "order_number": "61ec1afa-1b0e-4234-ae28-f997728054fa"
            }

        Returns a JSON object listing the signal receivers of
        fulfill_order_placed_signal.send_robust which processed the
        request.
        """
        logger.debug(f'Titan OrderFulfillView.post() request object: {request.data}.')
        logger.debug(f'Titan OrderFulfillView.post() headers: {request.headers}.')

        params = {
            'course_id': request.data.get('course_id'),
            'course_mode': request.data.get('course_mode'),
            'date_placed': request.data.get('order_placed'),
            'edx_lms_user_id': request.data.get('edx_lms_user_id'),
            'email_opt_in': request.data.get('email_opt_in'),
            'order_number': request.data.get('order_number'),
            'provider_id': request.data.get('provider'),
        }

        # TODO: add enterprise data for enrollment API here

        # TODO: add credit_provider data here
        # /ecommerce/extensions/fulfillment/modules.py#L315

        logger.info(f'Titan OrderFulfillView.post() called using {locals()}.')

        serializer = OrderFulfillViewInputSerializer(data=params)

        if serializer.is_valid(raise_exception=True):
            results = fulfill_order_placed_signal.send_robust(
                sender=self.__class__,
                **serializer.validated_data
            )
            return Response(format_signal_results(results))
        else:
            return None
