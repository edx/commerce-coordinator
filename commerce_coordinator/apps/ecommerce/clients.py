"""
API clients for ecommerce_caller app.
"""
import logging

import requests
from django.conf import settings

from commerce_coordinator.apps.core.clients import BaseEdxOAuthClient

logger = logging.getLogger(__name__)


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
