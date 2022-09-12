"""
Views for the titan app
"""

import logging

from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from commerce_coordinator.apps.core.signal_helpers import format_signal_results

from .signals import fulfill_order_placed_signal

logger = logging.getLogger(__name__)


class OrderFulfillView(APIView):
    """
    API for order fulfillment that is called from Titan.
    """
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
        coupon_code = request.data.get('coupon_code')
        course_id = request.data.get('course_id')
        date_placed = request.data.get('date_placed')
        edx_lms_user_id = request.data.get('edx_lms_user_id')
        edx_lms_username = request.data.get('edx_lms_username')
        mode = request.data.get('mode')
        partner_sku = request.data.get('partner_sku')
        titan_order_uuid = request.data.get('titan_order_uuid')

        # TODO: add enterprise data for enrollment API here

        # TODO: add credit_provider data here
        # /ecommerce/extensions/fulfillment/modules.py#L315

        logger.info(
            'Attempting to fulfill Titan order ID [%s] for user ID [%s], course ID [%s], on [%s]',
            titan_order_uuid,
            edx_lms_user_id,
            course_id,
            date_placed,
        )

        results = fulfill_order_placed_signal.send_robust(
            sender=self.__class__,
            date_placed=date_placed,
            edx_lms_user_id=edx_lms_user_id,
            edx_lms_username=edx_lms_username,
            course_id=course_id,
            coupon_code=coupon_code,
            mode=mode,
            partner_sku=partner_sku,
            titan_order_uuid=titan_order_uuid,
        )
        return Response(format_signal_results(results))
