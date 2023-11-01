"""
Views for the commercetools app
"""
import logging

from edx_rest_framework_extensions.permissions import LoginRedirectIfUnauthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from ..core.constants import ORDER_HISTORY_PER_SYSTEM_REQ_LIMIT
from .filters import OrderHistoryRequested

logger = logging.getLogger(__name__)


class UserOrdersView(APIView):
    """Get the order history for the authenticated user."""
    permission_classes = [LoginRedirectIfUnauthenticated]
    throttle_classes = [UserRateThrottle]

    def get(self, request):
        """Return paginated response of user's order history."""

        # build parameters
        params = {
            'username': request.user.username,
            "edx_lms_user_id": request.user.lms_user_id,
            "page": 0,
            "page_size": ORDER_HISTORY_PER_SYSTEM_REQ_LIMIT
        }

        # deny global queries
        if not request.user.username:
            raise PermissionDenied(detail="Could not detect username.")
        if not request.user.lms_user_id:
            raise PermissionDenied(detail="Could not detect LMS user id.")

        order_data = OrderHistoryRequested.run_filter(params)

        return Response({
            "order_data": sorted(order_data["order_data"], key=lambda item: item["date_placed"], reverse=True)
        })
