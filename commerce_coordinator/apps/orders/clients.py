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

        See sample response in tests.py

        """
        try:
            endpoint = self.api_base_url + 'orders/'
            response = self.client.get(endpoint, params=query_params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as exc:
            logger.exception(exc)
            raise
