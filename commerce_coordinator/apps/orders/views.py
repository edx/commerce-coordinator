"""
Views for the orders app
"""
import logging

from django.http import JsonResponse

from .clients import EcommerceApiClient

logger = logging.getLogger(__name__)


def get_user_orders__ecommerce(request):
    """
    To start: get orders from ecommerce for hardcode
    """
    username = request.GET['username']
    page = request.GET['page']
    page_size = request.GET['page_size']
    params = {'username': username, "page": page, "page_size": page_size}

    logger.info(f'DKTEST: get_user_orders__ecommerce called with params: {params}.')

    ecommerce_api_client = EcommerceApiClient()
    ecommerce_response = ecommerce_api_client.get_orders(params)

    return JsonResponse(ecommerce_response)
