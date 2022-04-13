"""
Views for the orders app
"""

from django.http import JsonResponse

from .clients import EcommerceApiClient


def get_user_orders__ecommerce(request):
    """
    To start: get orders from ecommerce for hardcode
    """
    username = request.GET['username']
    page = request.GET['page']
    page_size = request.GET['page_size']
    params = {username, page, page_size}

    ecommerce_api_client = EcommerceApiClient()
    ecommerce_response = ecommerce_api_client.get_orders(params)

    return JsonResponse(ecommerce_response)
