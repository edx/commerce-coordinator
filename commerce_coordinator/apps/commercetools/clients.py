"""
API clients for commercetools app.
"""
import logging

from commercetools import Client as CTClient
from django.conf import settings

# from requests.exceptions import RequestException

# from commerce_coordinator.apps.core.clients import BaseEdxOAuthClient, urljoin_directory

logger = logging.getLogger(__name__)


class CommercetoolsAPIClient:  # (BaseEdxOAuthClient): ???
    ct_api_client = None

    def __init__(self):
        super().__init__()
        config = settings.COMMERCETOOLS_CONFIG
        self.ct_api_client = CTClient(
            client_id=config["clientId"],
            client_secret=config["clientSecret"],
            scope=[config["scopes"]],
            url=config["apiUrl"],
            token_url=config["authUrl"],
            project_key=config["projectKey"]
        )

    def get_orders(self, query_params):
        """
        Call ecommerce API overview endpoint for data about an order.

        Arguments:
            edx_lms_user_id: restrict to orders by this username
        Returns:
            dict: Dictionary represention of JSON returned from API

        See sample response in tests.py

        """
        return None
        # try:
        #     resource_url = urljoin_directory(self.api_base_url, '/orders')
        #     response = self.client.get(resource_url, params=query_params)
        #     response.raise_for_status()
        #     self.log_request_response(logger, response)
        # except RequestException as exc:
        #     self.log_request_exception(logger, exc)
        #     raise
        # return response.json()
