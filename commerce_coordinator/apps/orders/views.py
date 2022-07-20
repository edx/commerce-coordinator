"""
Views for the orders app
"""
import logging

from edx_rest_framework_extensions.permissions import LoginRedirectIfUnauthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from .filters import OrderDataRequested

logger = logging.getLogger(__name__)


class UserOrdersView(APIView):
    """Get the order history for the authenticated user."""
    permission_classes = [LoginRedirectIfUnauthenticated]
    throttle_classes = [UserRateThrottle]

    def get(self, request):
        """Return paginated response of user's order history."""

        # deny global queries
        if not request.user.username:
            raise PermissionDenied(detail="Could not detect username.")
        order_data = OrderDataRequested.run_filter(request)
        return Response(order_data[0])
