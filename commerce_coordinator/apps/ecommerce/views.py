"""
Views for the ecommerce app
"""
from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from edx_rest_framework_extensions.permissions import LoginRedirectIfUnauthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from commerce_coordinator.apps.core.signal_helpers import format_signal_results

from .serializers import OrderCreatedSignalInputSerializer
from .signals import enrollment_code_redemption_requested_signal, order_created_signal


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
            product_sku: Array. An edx.org stock keeping units (SKUs) that the user would like to purchase.
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
            'product_sku': request.query_params.getlist('product_sku'),
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
