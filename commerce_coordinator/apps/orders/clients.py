"""
API clients for services that manage orders.
"""
import logging

import requests
from django.conf import settings
from edx_rest_api_client.client import OAuthAPIClient

logger = logging.getLogger(__name__)


class BaseEdxOAuthClient:
    """
    API client for calls to the other edX services.
    """

    def __init__(self):
        self.client = OAuthAPIClient(
            settings.SOCIAL_AUTH_EDX_OAUTH2_URL_ROOT.strip('/'),
            self.oauth2_client_id,
            self.oauth2_client_secret,
            timeout=(
                settings.REQUEST_CONNECT_TIMEOUT_SECONDS,
                settings.REQUEST_READ_TIMEOUT_SECONDS
            )
        )

    @property
    def oauth2_client_id(self):
        return settings.BACKEND_SERVICE_EDX_OAUTH2_KEY

    @property
    def oauth2_client_secret(self):
        return settings.BACKEND_SERVICE_EDX_OAUTH2_SECRET


class EcommerceApiClient(BaseEdxOAuthClient):
    """
    API client for calls to the edX Ecommerce service.
    """
    api_base_url = str(settings.ECOMMERCE_URL) + '/api/v2/'

    def get_orders(self, query_params):
        """
        Call ecommerce API overview endpoint for data about an order.

        Arguments:
            username: restrict to orders by this username
        Returns:
            dict: Dictionary represention of JSON returned from API

        example response:
        {
            {"count": 1, "next": null, "previous": null, "results": [{"billing_address": {"first_name":
            "Diane", "last_name": "Test", "line1": "50 turner st", "line2": "", "postcode": "02135",
            "state": "MA", "country": "US", "city": "Brighton"}, "currency": "USD", "date_placed":
            "2021-12-20T15:09:44Z", "discount": "0", "lines": [{"title": "Seat in edX Demonstration
            Course with verified certificate (and ID verification)", "quantity": 1, "description":
            "Seat in edX Demonstration Course with verified certificate (and ID verification)", "status":
            "Complete", "line_price_excl_tax": "149.00", "unit_price_excl_tax": "149.00", "product":
            {"id": 3, "url": "http://localhost:18130/api/v2/products/3/", "structure": "child",
            "product_class": "Seat", "title": "Seat in edX Demonstration Course with verified certificate
            (and ID verification)", "price": "149.00", "expires": "2022-11-08T22:54:30.777313Z",
            "attribute_values": [{"name": "certificate_type", "code": "certificate_type", "value":
            "verified"}, {"name": "course_key", "code": "course_key", "value":
            "course-v1:edX+DemoX+Demo_Course"}, {"name": "id_verification_required", "code":
            "id_verification_required", "value": true}], "is_available_to_buy": true, "stockrecords":
            [{"id": 3, "product": 3, "partner": 1, "partner_sku": "8CF08E5", "price_currency": "USD",
            "price_excl_tax": "149.00"}]}}], "number": "EDX-100004", "payment_processor":
            "cybersource-rest", "status": "Complete", "total_excl_tax": "149.00", "user":
            {"email": "edx@example.com", "username": "edx"}, "vouchers": []} ]}
        }
        """
        try:
            endpoint = self.api_base_url + 'orders/'
            response = self.client.get(endpoint, params=query_params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as exc:
            logger.exception(exc)
            raise
