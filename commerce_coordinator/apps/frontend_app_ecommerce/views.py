"""
Views for the frontend_app_ecommerce app
"""
import logging
from datetime import datetime
from typing import Union

from dateutil import parser as dateparser
from django.http import HttpResponseBadRequest, HttpResponseNotFound, HttpResponseRedirect
from edx_rest_framework_extensions.permissions import LoginRedirectIfUnauthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.status import HTTP_303_SEE_OTHER
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

        user = request.user
        user.add_lms_user_id("RedirectReceiptView GET method")
        order_number = request.query_params.get('order_number', None)

        if not order_number:
            return HttpResponseBadRequest("Invalid order number supplied.")

        # build parameters
        params = {
            'username': request.user.username,
            "edx_lms_user_id": request.user.lms_user_id,
            "order_number": order_number,
        }

        redirect_url = OrderReceiptRedirectionUrlRequested.run_filter(
            params=params,
            order_number=params['order_number']
        )

        if redirect_url:
            redirect = HttpResponseRedirect(redirect_url, status=HTTP_303_SEE_OTHER)
            redirect.headers[HttpHeadersNames.CACHE_CONTROL.value] = "max-age=2591000"  # 16ish mins short of 30 days
            return redirect
        else:
            return HttpResponseNotFound("Something went wrong.")


# noinspection PyMethodMayBeStatic
class UserOrdersView(APIView):
    """Get the order history for the authenticated user."""
    permission_classes = [LoginRedirectIfUnauthenticated]
    throttle_classes = [UserRateThrottle]

    def get(self, request):
        """Return paginated response of user's order history."""
        request_start_time = datetime.now()
        logger.info("[UserOrdersView] GET method started at: %s", request_start_time)

        user = request.user
        user.add_lms_user_id("UserOrdersView GET method")
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

        start_time = datetime.now()
        logger.info("[UserOrdersView] Pipline filter run started at: %s", start_time)
        order_data = OrderHistoryRequested.run_filter(request, params)
        end_time = datetime.now()
        logger.info("[UserOrdersView] Pipline filter run finished at: %s with total duration: %ss",
                    end_time, (end_time - start_time).total_seconds())

        output_orders = []

        start_time = datetime.now()
        logger.info("[UserOrdersView] Looping through combined orders results starting at: %s", start_time)
        for order_set in order_data:
            output_orders.extend(order_set['results'])

        end_time = datetime.now()
        logger.info(
            "[UserOrdersView] Looping through combined orders results finished at: %s with total duration: %ss",
            end_time, (end_time - start_time).total_seconds())

        start_time = datetime.now()
        logger.info("[UserOrdersView] Sorting combined orders results for output starting at: %s", start_time)
        output = {
            "count": request.query_params['page_size'],  # This suppresses the ecomm mfe Order History Pagination ctrl
            "next": None,
            "previous": None,
            "results": sorted(output_orders, key=lambda item: date_conv(item["date_placed"]), reverse=True)
        }

        end_time = datetime.now()
        logger.info(
            "[UserOrdersView] Sorting combined orders results for output finished at: %s with total duration: %ss",
            end_time, (end_time - start_time).total_seconds())

        request_end_time = datetime.now()
        logger.info("[UserOrdersView] GET method finished at: %s with total duration: %ss", request_end_time,
                    (request_end_time - request_start_time).total_seconds())
        return Response(output)
