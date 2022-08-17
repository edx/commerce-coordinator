"""
Views for the ecommerce app
"""
from edx_rest_framework_extensions.permissions import LoginRedirectIfUnauthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from commerce_coordinator.apps.core.signal_helpers import format_signal_results

from .signals import enrollment_code_redemption_requested_signal


class RedeemEnrollmentCodeView(APIView):
    """User requests to redeem enrollment code."""
    permission_classes = [LoginRedirectIfUnauthenticated]
    throttle_classes = [UserRateThrottle]

    def get(self, request):
        """Return paginated response of user's order history."""

        code = request.query_params.get('code')
        sku = request.query_params.get('sku')

        if not code:
            return Response({'error': 'Code not provided.'})
        if not sku:
            return Response({'error': 'SKU not provided.'})

        results = enrollment_code_redemption_requested_signal.send_robust(
            sender=self.__class__,
            user_id=request.user.id,
            sku=sku,
            enrollment_code=code,
        )

        return Response(format_signal_results(results))
