"""
Views for the ecommerce app
"""
import logging
from urllib.parse import unquote, urlencode

from django.http import HttpResponseBadRequest, HttpResponseRedirect
from edx_rest_framework_extensions.permissions import LoginRedirectIfUnauthenticated
from rest_framework.status import HTTP_303_SEE_OTHER
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from commerce_coordinator.apps.core.constants import HttpHeadersNames, MediaTypes
from commerce_coordinator.apps.lms.filters import PaymentPageRedirectRequested

logger = logging.getLogger(__name__)


class PaymentPageRedirectView(APIView):
    """Accept incoming request for routing users to checkout view."""
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
        except Exception as e:  # pylint: disable=broad-except
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
        query_params = unquote(query_params)
        url = url + '?' + query_params if query_params else url

        return url
