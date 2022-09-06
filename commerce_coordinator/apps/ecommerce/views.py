"""
Views for the ecommerce app
"""
from edx_rest_framework_extensions.permissions import LoginRedirectIfUnauthenticated
from rest_framework.exceptions import PermissionDenied
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
        """
        Redeem an enrollment code for an authenticated user.

        Args:
            sku: ecommerce partner_sku to be redeemed
            code: enrollment code (aka, 100 percent off coupon code) to redeem.

        Returns:
            Dictionary with results from signal dispatch to redeem an enrollment code.

        Raises:
            PermissionDenied: Djano was unable to determine the user's id or email.
        """

        sku = request.query_params.get('sku')
        code = request.query_params.get('code')

        if not request.user.id or not request.user.email:
            raise PermissionDenied(detail="Could not detect user id or email.")
        if not sku:
            return Response({'error': 'SKU not provided.'})
        if not code:
            return Response({'error': 'Code not provided.'})

        results = enrollment_code_redemption_requested_signal.send_robust(
            sender=self.__class__,
            user_id=request.user.id,
            email=request.user.email,
            sku=sku,
            coupon_code=code,
        )

        return Response(format_signal_results(results))
