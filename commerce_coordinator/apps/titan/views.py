"""
Views for the titan app
"""

import logging

from edx_rest_framework_extensions.permissions import LoginRedirectIfUnauthenticated
from rest_framework import status
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from .serializers import OrderFulfillSerializer

logger = logging.getLogger(__name__)


class OrderFulfillView(APIView):
    """
    API for order fulfillment that is called from Titan.
    """
    permission_classes = [LoginRedirectIfUnauthenticated]
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    throttle_classes = [UserRateThrottle]

    serializer_class = OrderFulfillSerializer

    def post(self, request):
        """
        POST request handler for /order/fulfill
        Requires a JSON object of the following format:
        {
            "coupon_code": "WELCOME100",
            "course_id": "course-v1:edX+DemoX+Demo_Course",
            "date_placed": "2022-08-24T16:57:00.127327+00:00",
            "edx_lms_user_id": 1,
            "mode": "verified",
            "partner_sku": "test-sku",
            "titan_order_uuid": "123-abc",
            "edx_lms_username": "test-user"
        }
        Returns a JSON object of the following format:
        {
            "<function fulfill_order_placed_send_enroll_in_course at 0x105088700>": {
              "response": "",
              "error": false
            },
        }
        """
        # TODO: below commented code is without a serializer
        # edx_lms_user_id = request.data.get('edx_lms_user_id')
        # # edx_lms_user_id = request.POST.get('edx_lms_user_id')
        # # edx_lms_user_id = request.user.id
        # partner_sku = request.data.get('partner_sku')
        # titan_order_id = request.data.get('titan_order_id')
        # coupon_code = request.data.get('coupon_code')
        # course_id = request.data.get('course_id')
        # data = {
        #     "edx_lms_user_id": edx_lms_user_id,
        #     "sku": partner_sku,
        #     "titan_order_id": titan_order_id,
        #     "coupon_code": coupon_code,
        # }
        # By default REST framework's APIView  class will raise an error if
        # the client data is malformed and return a 400 Bad Request response.
        # return Response(data, status=status.HTTP_201_CREATED)

        # deny global queries
        if not request.user.username:
            raise PermissionDenied(detail="Could not detect username.")

        titan_order_id = request.data.get('titan_order_id')
        coupon_code = request.data.get('coupon_code')
        logger.info('Fulfillment requested for titan order id [%s] and coupon code [%s].', titan_order_id, coupon_code)

        serializer = OrderFulfillSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
