"""
Views for the ecommerce app
"""

from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from edx_rest_framework_extensions.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from .filters import OrderCreateRequested
from .serializers import OrderCreatedSignalInputSerializer

# TODO: Once we are live for good, kill this and default the lines as expected.
IS_LIVE = False


class OrderCreateView(APIView):
    """Accept incoming request for creating a basket/order for a user."""
    authentication_classes = (JwtAuthentication,)
    permission_classes = (IsAuthenticated,)
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
            'edx_lms_user_id': request.user.lms_user_id if IS_LIVE else request.query_params.get('edx_lms_user_id'),
            'email': request.user.email if IS_LIVE else request.query_params.get('email'),
            'first_name': request.user.first_name if IS_LIVE else 'John',
            'last_name': request.user.last_name if IS_LIVE else 'Doe',
            'coupon_code': request.query_params.get('coupon_code'),
        }
        serializer = OrderCreatedSignalInputSerializer(data=order_created_signal_params)

        if serializer.is_valid(raise_exception=True):
            result = OrderCreateRequested.run_filter(serializer.validated_data)
            return Response(result)
