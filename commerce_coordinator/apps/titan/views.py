"""
Views for the titan app
"""

import logging

from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
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
    throttle_classes = [UserRateThrottle]

    def post(self, request):
        """
        POST request handler for /order/fulfill

        Requires a JSON object of the following format:
            {
                "coupon_code": "WELCOME100",
                "course_id": "course-v1:edX+DemoX+Demo_Course",
                "date_placed": "2022-08-24T16:57:00.127327+00:00",
                "edx_lms_user_id": 1,
                "edx_lms_username": "test-user",
                "mode": "verified",
                "partner_sku": "test-sku",
                "titan_order_uuid": "123-abc",

            }

        Returns a JSON object of the following format:
            {
                "<function fulfill_order_placed_send_enroll_in_course at 0x105088700>": {
                    "response": "",
                    "error": false,

                },

            }
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
