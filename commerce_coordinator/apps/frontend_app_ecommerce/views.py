"""
Views for the frontend_app_ecommerce app
"""
import logging
from datetime import datetime
from typing import Union

from dateutil import parser as dateparser
from django.http import HttpResponse, HttpResponseRedirect
from edx_rest_framework_extensions.permissions import LoginRedirectIfUnauthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.status import HTTP_303_SEE_OTHER, HTTP_404_NOT_FOUND
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from commerce_coordinator.apps.core.constants import ORDER_HISTORY_PER_SYSTEM_REQ_LIMIT, HttpHeadersNames
from commerce_coordinator.apps.frontend_app_ecommerce.filters import (
    OrderHistoryRequested,
    OrderReceiptRedirectionUrlRequested
)

logger = logging.getLogger(__name__)


def date_conv(dt: Union[datetime, str]) -> datetime:
    if isinstance(dt, str):
        return dateparser.parse(dt)
    else:
        return dt


# noinspection PyMethodMayBeStatic
class RedirectReceiptView(APIView):
    """Get the order history for the authenticated user."""
    permission_classes = [LoginRedirectIfUnauthenticated]
    throttle_classes = [UserRateThrottle]

    def get(self, request):
        """Get the order history for the authenticated user."""

        # build parameters
        params = {
            'username': request.user.username,
            "edx_lms_user_id": request.user.lms_user_id,
            "order_number": request.query_params.get('order_number', None),
        }

        # deny global queries
        if not request.user.username:  # pragma: no cover
            # According to the Django checks, this isn't possible with our current user model.
            # Leaving in incase that changes.
            raise PermissionDenied(detail="Could not detect username.")
        if not request.user.lms_user_id:  # pragma: no cover
            raise PermissionDenied(detail="Could not detect LMS user id.")

        redirect_url = OrderReceiptRedirectionUrlRequested.run_filter(params, order_number=params['order_number'])

        if redirect_url:
            redirect = HttpResponseRedirect(redirect_url, status=HTTP_303_SEE_OTHER)
            redirect.headers[HttpHeadersNames.CACHE_CONTROL.value] = "max-age=2591000"  # 16ish mins short of 30 days
            return redirect
        else:
            return HttpResponse(status=HTTP_404_NOT_FOUND)


# noinspection PyMethodMayBeStatic
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
        if not request.user.username:  # pragma: no cover
            # According to the Django checks this isnt possible with our current user model.
            # Leaving in incase that changes.
            raise PermissionDenied(detail="Could not detect username.")
        if not request.user.lms_user_id:  # pragma: no cover
            raise PermissionDenied(detail="Could not detect LMS user id.")

        order_data = OrderHistoryRequested.run_filter(params)

        output_orders = []

        for order_set in order_data:
            output_orders.extend(order_set['results'])

        return Response(sorted(output_orders, key=lambda item: date_conv(item["date_placed"]), reverse=True))
