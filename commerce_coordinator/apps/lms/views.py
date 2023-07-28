"""
Views for the ecommerce app
"""
import logging
from urllib.parse import unquote, urlencode

from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponseServerError
from edx_rest_framework_extensions.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from .filters import OrderCreateRequested
from .serializers import OrderCreatedSignalInputSerializer
from ..core.auth import ForceCookieJwtAuthentication
from ..core.content_negotiation import IgnoreClientContentNegotiation

logger = logging.getLogger(__name__)


class OrderCreateView(APIView):
    """Accept incoming request for creating a basket/order for a user."""
    authentication_classes = (ForceCookieJwtAuthentication,)
    permission_classes = (IsAuthenticated,)
    throttle_classes = (UserRateThrottle,)
    content_negotiation_class = IgnoreClientContentNegotiation

    def get(self, request):  # pylint: disable=inconsistent-return-statements
        """
        Create orders for an authenticated user.

        Args:
            request (django.http.HttpRequest): django.http.HttpRequest

        Query Parameters:
            sku: Array. An edx.org stock keeping units (SKUs) that the user would like to purchase.
            coupon_code: (Optional) A coupon code to initially apply to the order.

        Returns:
            an HTTP Response, in the form of an error or as an HTTP Redirect.

            - HTTP Redirect (303): Redirection to Payment MFE upon Success
            - HTTP File or Server Error (400-599) see Errors section for more information.

        Errors:
            - 400: if required params are missing or not in supported format.
            - 401: if user is unauthorized.

        """
        logger.debug(f'{self.get.__qualname__} request object: {request.data}.')
        logger.debug(f'{self.get.__qualname__} headers: {request.headers}.')

        order_created_signal_params = {
            'sku': request.query_params.getlist('sku'),
            'edx_lms_user_id': request.user.lms_user_id,
            'email': request.user.email,
            'first_name': request.user.first_name if len(str(request.user.first_name).strip()) > 1 else None,
            'last_name': request.user.last_name if len(str(request.user.last_name).strip()) > 1 else None,
            'coupon_code': request.query_params.get('coupon_code'),
        }
        serializer = OrderCreatedSignalInputSerializer(data=order_created_signal_params)

        if serializer.is_valid(raise_exception=True):
            try:
                result = OrderCreateRequested.run_filter(serializer.validated_data)
                logger.debug(f'{self.get.__qualname__} pipeline result: {result}.')

                return self._redirect_response_payment(request)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.exception(f"Something went wrong! Exception raised in {self.get.__name__} with error {repr(e)}")
                return HttpResponseServerError()

        # Log for Diagnostics
        logger.debug(f'{self.get.__qualname__} we didnt redirect..')  # pragma: no cover

    def _redirect_response_payment(self, request):
        """
        Redirect to Payment MFE with its Adornments (like UTM).

        Args:
            request (django.HttpRequest):
        Returns:
            response (django.HttpResponse):
        """

        redirect_url = self._add_utm_params_to_url(
            settings.PAYMENT_MICROFRONTEND_URL,
            list(self.request.GET.items())
        )

        redirect = HttpResponseRedirect(redirect_url, status=303)
        redirect.headers['Content-type'] = 'application/json'
        logger.debug(f'{self._redirect_response_payment.__qualname__} Redirecting 303 via {redirect}.')
        return redirect

    @staticmethod
    def _add_utm_params_to_url(url, params):
        """
        Add UTM (Urchin Tracking/Google Analytics) flags to the URL for the MFE to use in its reporting

        Args:
            params (list): Query Params from Req as an encoded list
        Returns:
            url (str): A URL asa Python String
        """

        # utm_params is [(u'utm_content', u'course-v1:IDBx IDB20.1x 1T2017'),...
        utm_params = [item for item in params if 'utm_' in item[0]]
        # utm_params is utm_content=course-v1%3AIDBx+IDB20.1x+1T2017&...
        utm_params = urlencode(utm_params, True)
        # utm_params is utm_content=course-v1:IDBx+IDB20.1x+1T2017&...
        # (course-keys do not have url encoding)
        utm_params = unquote(utm_params)
        url = url + '?' + utm_params if utm_params else url
        return url
