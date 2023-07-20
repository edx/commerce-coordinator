"""
Views for the ecommerce app
"""
import logging

from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from edx_rest_framework_extensions.permissions import LoginRedirectIfUnauthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from commerce_coordinator.apps.core.models import User
from commerce_coordinator.apps.core.signal_helpers import format_signal_results

from .serializers import OrderCreatedSignalInputSerializer, OrderFulfillViewInputSerializer
from .signals import enrollment_code_redemption_requested_signal, fulfill_order_placed_signal, order_created_signal

logger = logging.getLogger(__name__)


class RedeemEnrollmentCodeView(APIView):
    """User requests to redeem enrollment code."""
    permission_classes = [LoginRedirectIfUnauthenticated]
    throttle_classes = [UserRateThrottle]

    def get(self, request):
        """
        Redeem an enrollment code for an authenticated user.

        Args:
            sku: ecommerce partner_sku to be redeemed
            code: enrollment code (aka, 100 percent off coupon code) to redeem.

        Returns:
            Dictionary with results from signal dispatch to redeem an enrollment code.

        Raises:
            PermissionDenied: Djano was unable to determine the user's id, username, or email.
        """

        sku = request.query_params.get('sku')
        code = request.query_params.get('code')

        if not request.user.id:
            raise PermissionDenied(detail="Could not detect user id.")
        if not request.user.username:
            raise PermissionDenied(detail="Could not detect username.")
        if not request.user.email:
            raise PermissionDenied(detail="Could not detect user email.")

        if not sku:
            return Response({'error': 'SKU not provided.'})
        if not code:
            return Response({'error': 'Code not provided.'})

        results = enrollment_code_redemption_requested_signal.send_robust(
            sender=self.__class__,
            user_id=request.user.id,
            username=request.user.username,
            email=request.user.email,
            sku=sku,
            coupon_code=code,
        )

        return Response(format_signal_results(results))


class OrderCreateView(APIView):
    """Accept Ecommerce request for creating a basket/order for a user."""
    authentication_classes = (JwtAuthentication,)
    # TODO: Change permission_classes to edx_rest_framework_extensions.permissions.IsAuthenticated
    permission_classes = (IsAdminUser,)
    throttle_classes = (UserRateThrottle,)

    def get(self, request):  # pylint: disable=inconsistent-return-statements
        """
        Create orders for an authenticated user.

        Args:
            sku: Array. An edx.org stock keeping units (SKUs) that the user would like to purchase.
            coupon_code: (Optional) A coupon code to initially apply to the order.
            edx_lms_user_id: (Temporary) Initially we will be calling this API from a server. this param is to bypass
                the edx_lms_user_id from the calling server. later on, we will remove this param and extract
                edx_lms_user_id from request.user.lms_user_id.

        Returns:
            order_created_save:
                error: Boolean: Represents if there was error in releasing signal

        Errors:
            400: if required params are missing or not in supported format.
            401: if user is unauthorized.

        """
        order_created_signal_params = {
            'sku': request.query_params.getlist('sku'),
            # TODO: edx_lms_user_id should be taken from request.user.lms_user_id once we go live.
            'edx_lms_user_id': request.query_params.get('edx_lms_user_id'),
            # TODO: email should be taken from request.user.email once we go live.
            'email': request.query_params.get('email'),
            # TODO: first_name, last_name should be taken from request.user once we go live.
            'first_name': 'John',
            'last_name': 'Doe',
            'coupon_code': request.query_params.get('coupon_code'),
        }
        serializer = OrderCreatedSignalInputSerializer(data=order_created_signal_params)
        if serializer.is_valid(raise_exception=True):
            results = order_created_signal.send_robust(
                sender=self.__class__,
                **serializer.validated_data
            )
            return Response(format_signal_results(results))


class OrderFulfillView(APIView):
    """
    API for order fulfillment that is called from Ecommerce.
    """
    permission_classes = [IsAdminUser]
    throttle_classes = [UserRateThrottle]

    def post(self, request):  # pylint: disable=inconsistent-return-statements
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
        logger.debug(f'Ecommerce OrderFulfillView.post() request object: {request.data}.')
        logger.debug(f'Ecommerce OrderFulfillView.post() headers: {request.headers}.')

        params = {
            'course_id': request.data.get('course_id'),
            'course_mode': request.data.get('course_mode'),
            'date_placed': request.data.get('order_placed'),
            'email_opt_in': request.data.get('email_opt_in'),
            'order_number': request.data.get('order_number'),
            'provider_id': request.data.get('provider'),
            'user': request.data.get('user'),
        }

        logger.info(f'Ecommerce OrderFulfillView.post() called using {locals()}.')

        serializer = OrderFulfillViewInputSerializer(data=params)

        if serializer.is_valid(raise_exception=True):
            payload = serializer.validated_data

            # Replace username with LMS user id.
            translated_user_id = User.objects.get(username=payload['user']).lms_user_id
            logger.info('Ecommerce OrderFulfillView.post() translated username [%s] into LMS user id [%s].',
                        payload['user'],
                        translated_user_id,
                        )
            payload['edx_lms_user_id'] = translated_user_id
            payload.pop('user')

            results = fulfill_order_placed_signal.send_robust(
                sender=self.__class__,
                **payload
            )
            return Response(format_signal_results(results))
