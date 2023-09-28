"""
Views for the commercetools app
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

        # TODO: GRM: Implement (finish w/sorting by date and trimming)

        # build parameters
        page = request.query_params.get("page")
        page_size = request.query_params.get("page_size")
        params = {'username': request.user.username, "page": page, "page_size": page_size}

        # Because were getting results from 2 systems, page_size becomes page_size*2 results (potentially) and must be
        # trimmed at page_size.

        # deny global queries
        if not request.user.username:
            raise PermissionDenied(detail="Could not detect username.")
        if not request.user.lms_user_id:
            raise PermissionDenied(detail="Could not detect LMS user id.")
        order_data = OrderHistoryRequested.run_filter(params)

        return Response(order_data)
