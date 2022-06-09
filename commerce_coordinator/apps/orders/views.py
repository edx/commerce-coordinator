"""
Views for the orders app
"""
import logging

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect

from .clients import EcommerceApiClient

logger = logging.getLogger(__name__)


def redirect_user_orders__ecommerce(request):
    """
    Redirects user to ecommerce API for getting orders.
    """
    api_url = str(settings.ECOMMERCE_URL) + '/api/v2/orders/'

    # The query string is get_full_path without the leading path.
    query_string = request.get_full_path().replace(request.path, "", 1)

    return redirect(api_url + query_string)


def get_user_orders__ecommerce(request):
    """
    To start: get orders from ecommerce for hardcode
    """
    username = request.GET['username']
    page = request.GET['page']
    page_size = request.GET['page_size']
    params = {'username': username, "page": page, "page_size": page_size}

    ecommerce_api_client = EcommerceApiClient()
    ecommerce_response = ecommerce_api_client.get_orders(params)
    return JsonResponse(ecommerce_response)
