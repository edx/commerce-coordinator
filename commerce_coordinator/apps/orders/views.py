"""
Views for the orders app
"""

from django.http import JsonResponse
from .clients import EcommerceApiClient

def get_user_orders__ecommerce(_):
    """
    To start: get orders from ecommerce for hardcode
    """

    # @@TODO: Once these are working, move them to the right place
    ECOMMERCE_BASE_URL = 'http://localhost:18130'
    ECOMMERCE_API_BASE_URL = ECOMMERCE_BASE_URL + '/api/v2'

    # hardcode to get working, then figure out how to pass them inn
    username = 'edx'
    one = 1

    params= {
      username,
      one,
      one,
    }

    url_to_hit = f'{ECOMMERCE_API_BASE_URL}/orders/?page={one}&page_size={one}&username={username}'

    ecommerce_api_client = EcommerceApiClient()
    ecommerce_response = ecommerce_api_client.get_orders(username)

    # print('DKTEST ecommerce_response: ', ecommerce_response)

    # requests.get(url_to_hit, params=params) # ValueError at /orders/test/, too many values to unpack (expected 2)

    return JsonResponse(ecommerce_response)
