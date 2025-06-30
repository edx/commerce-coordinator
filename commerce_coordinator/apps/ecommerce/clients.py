"""
API clients for ecommerce app.
"""
import logging

from django.conf import settings
from requests.exceptions import RequestException

from commerce_coordinator.apps.core.clients import BaseEdxOAuthClient, urljoin_directory

logger = logging.getLogger(__name__)


class EcommerceAPIClient(BaseEdxOAuthClient):
    """
    API client for calls to the edX Ecommerce service.
    """
    api_base_url = ""

    def __init__(self):
        super().__init__()
        self.base_url = settings.ECOMMERCE_URL
        self.api_base_url = urljoin_directory(settings.ECOMMERCE_URL, '/api/v2')

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
            resource_url = urljoin_directory(self.api_base_url, '/orders')
            response = self.client.get(resource_url, params=query_params)
            response.raise_for_status()
        except RequestException as exc:
            self.log_request_exception("[EcommerceAPIClient.get_orders]", logger, exc)
            raise

        return response.json()

    def refund_for_ios(self, payload) -> None:
        """
        Refund an order for iOS.

        Arguments:
            payload: Payload to pass as request body.
        """
        try:
            resource_url = urljoin_directory(self.base_url, 'api/iap/v1/ios/refund/')
            response = self.client.post(resource_url, json=payload)
            response.raise_for_status()
        except RequestException as exc:
            self.log_request_exception("[EcommerceAPIClient.refund_for_ios]", logger, exc)
            raise
