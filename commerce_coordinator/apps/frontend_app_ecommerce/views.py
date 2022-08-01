"""
Views for the frontend_app_ecommerce app
"""
import logging

from edx_rest_framework_extensions.permissions import LoginRedirectIfUnauthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from .filters import OrderHistoryRequested

logger = logging.getLogger(__name__)


class UserOrdersView(APIView):
    """Get the order history for the authenticated user."""
    permission_classes = [LoginRedirectIfUnauthenticated]
    throttle_classes = [UserRateThrottle]

    def get(self, request):
        """Return paginated response of user's order history."""

        # build parameters
        page = request.query_params.get("page")
        page_size = request.query_params.get("page_size")
        params = {'username': request.user.username, "page": page, "page_size": page_size}

        # deny global queries
        if not request.user.username:
            raise PermissionDenied(detail="Could not detect username.")
        order_data = OrderHistoryRequested.run_filter(params)

        return Response(order_data)
