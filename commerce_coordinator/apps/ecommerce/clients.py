"""
API clients for ecommerce app.
"""
import logging
from datetime import datetime

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
            start_time = datetime.now()
            logger.info(
                '[UserOrdersView] Legacy ecommerce get_orders API called at: %s',
                start_time
            )
            response = self.client.get(resource_url, params=query_params)
            end_time = datetime.now()
            logger.info(
                '[UserOrdersView] Legacy ecommerce get_orders API finished at: %s with total duration: %s',
                end_time, end_time - start_time
            )
            response.raise_for_status()
            self.log_request_response(logger, response)
        except RequestException as exc:
            self.log_request_exception(logger, exc)
            raise

        return response.json()
