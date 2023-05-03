"""
API clients for ecommerce app.
"""
import logging

import requests
from django.conf import settings

from commerce_coordinator.apps.core.clients import BaseEdxOAuthClient, urljoin_directory

logger = logging.getLogger(__name__)


class EcommerceAPIClient(BaseEdxOAuthClient):
    """
    API client for calls to the edX Ecommerce service.
    """
    api_base_url = ""

    def __init__(self):
        super().__init__()
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
            response_json = response.json()
            self.log_request_response(logger, response)
            return response_json
        except (requests.exceptions.HTTPError, requests.exceptions.JSONDecodeError) as exc:
            self.log_request_exception(logger, exc)
            raise
