"""
Views for the ecommerce app
"""
import logging
from urllib.parse import urlencode, urljoin

from django.conf import settings
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from edx_rest_framework_extensions.permissions import LoginRedirectIfUnauthenticated
from openedx_filters.exceptions import OpenEdxFilterException
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.status import HTTP_303_SEE_OTHER
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from commerce_coordinator.apps.core.constants import HttpHeadersNames, MediaTypes
from commerce_coordinator.apps.rollout.utils import is_legacy_order

from .filters import OrderRefundRequested, PaymentPageRedirectRequested
from .serializers import OrderRefundRequestedFilterInputSerializer, RefundViewInputSerializer

logger = logging.getLogger(__name__)


class PaymentPageRedirectView(APIView):
    """Accept incoming request for routing users to the checkout view."""
    permission_classes = (LoginRedirectIfUnauthenticated,)
    throttle_classes = (UserRateThrottle,)

    def get(self, request):
        """
        Routes learners to desired checkout view

        Args:
            request (django.http.HttpRequest): django.http.HttpRequest

        Returns:
            an HTTP Response, in the form of an error or as an HTTP Redirect.

            - HTTP Redirect (303): Redirection to correct checkout page upon Success
            - HTTP File or Server Error (400-599) see Errors section for more information.

        Errors:
            - 400: if required params are missing or not in supported format.
            - 401: if user is unauthorized.

        """
        logger.debug(f'{self.get.__qualname__} request object: {request.data}.')
        logger.debug(f'{self.get.__qualname__} headers: {request.headers}.')

        try:
            return self._redirect_response_payment(request)
        except OpenEdxFilterException as e:
            logger.exception(f"Something went wrong! Exception raised in {self.get.__name__} with error {repr(e)}")
            return HttpResponseBadRequest('Something went wrong.')

    def _redirect_response_payment(self, request):
        """
        Redirect to desired checkout view

        Args:
            request (django.HttpRequest):
        Returns:
            response (django.HttpResponse):
        """

        get_items = list(self.request.GET.items())

        redirect_url_obj = PaymentPageRedirectRequested.run_filter(request)

        redirect_url = self._add_query_params_to_redirect_url(
            redirect_url_obj['redirect_url'],
            get_items
        )

        redirect = HttpResponseRedirect(redirect_url, status=HTTP_303_SEE_OTHER)
        redirect.headers[HttpHeadersNames.CONTENT_TYPE.value] = MediaTypes.JSON.value
        logger.debug(f'{self._redirect_response_payment.__qualname__} Redirecting 303 via {redirect}.')
        return redirect

    @staticmethod
    def _add_query_params_to_redirect_url(url, params):
        """
        Add query params to the URL for the MFE to use in its reporting
        Args:
            params (list): Query Params from Req as an encoded list
        Returns:
            url (str): A URL asa Python String
        """

        query_params = list(params)
        query_params = urlencode(query_params, True)
        url = url + '?' + query_params if query_params else url

        return url


class OrderDetailsRedirectView(APIView):
    """Accept incoming request from the support tools MFE for routing staff users to the order details admin page."""
    permission_classes = [IsAdminUser]
    throttle_classes = (UserRateThrottle,)

    def get(self, request):
        """
        Routes staff to desired order details admin view.

        Args:
            request (django.http.HttpRequest): django.http.HttpRequest

        Returns:
            - HTTP Redirect (303): Redirection to correct checkout page upon Success

        Errors:
            - 400: if required params are missing or not in supported format.
            - 401: if user is unauthorized.

        """
        params = dict(request.GET.items())
        if not params.get('order_number', None):
            return HttpResponseBadRequest('Invalid order number supplied.')

        redirect_url = self._get_redirect_url(params)

        return HttpResponseRedirect(redirect_url, status=HTTP_303_SEE_OTHER)

    @staticmethod
    def _get_redirect_url(params):
        """
        Construct order details page URL based on the e-commerce source system.
        Args:
            params (dict): Query params from request as a dictionary
        Returns:
            url (str): A URL as a Python String
        """
        order_number = params.get('order_number')

        if is_legacy_order(order_number):
            url = urljoin(settings.ECOMMERCE_URL, f'{settings.ECOMMERCE_ORDER_DETAILS_DASHBOARD_PATH}{order_number}')
        else:
            ct_query_params = {
                'mode': 'basic',
                'searchMode': 'orderNumber',
                'searchTerm': f'{order_number}'
            }
            query_params = urlencode(ct_query_params, True)
            url = f'{settings.COMMERCETOOLS_MERCHANT_CENTER_ORDERS_PAGE_URL}?{query_params}'

        return url


class RefundView(APIView):
    """Accept incoming request from LMS for routing staff users to the order details admin page."""
    permission_classes = [IsAdminUser]

    def post(self, request):
        """
        POST request handler for /refund

        Requires a JSON object of the following format:

        .. code-block:: json

            {
                "course_id": "course-v1:edX+DemoX+Demo_Course",
                "course_mode": "verified",
                "order_placed": 1681738233,
                "edx_lms_user_id": 4,
                "email_opt_in": 0,
                "order_number": "61ec1afa-1b0e-4234-ae28-f997728054fa"
            }

        Returns a JSON object listing the signal receivers of
        fulfill_order_placed_signal.send_robust which processed the
        request.
        """
        logger.debug(f'LMS RefundView.post() request object: {request.data}.')
        logger.debug(f'LMS RefundView.post() headers: {request.headers}.')

        params = {
            'course_id': request.data.get('course_id'),
            'enrollment_attributes': request.data.get('enrollment_attributes'),
            'username': request.data.get('username'),
        }

        logger.info(f'LMS RefundView.post() called using {locals()}.')

        view_serializer = RefundViewInputSerializer(data=params)
        view_serializer.is_valid(raise_exception=True)

        filter_serializer = OrderRefundRequestedFilterInputSerializer(
            data=view_serializer.data
        )
        filter_serializer.is_valid(raise_exception=True)

        results = OrderRefundRequested.run_filter(
            **filter_serializer.data
        )

        return Response(results)
