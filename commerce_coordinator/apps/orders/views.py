"""
Views for the orders app
"""

from django.http import JsonResponse
from .clients import EcommerceApiClient

def get_user_orders__ecommerce(_):
    """
    To start: get orders from ecommerce for hardcode
    """

    # hardcode to get working, then figure out how to pass them inn
    username = 'edx'

    ecommerce_api_client = EcommerceApiClient()
    ecommerce_response = ecommerce_api_client.get_orders(username)


    return JsonResponse(ecommerce_response)
