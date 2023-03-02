"""
API clients for Titan.
"""
from urllib.parse import urljoin

import requests
from celery.utils.log import get_task_logger
from django.conf import settings
from edx_rest_api_client.client import OAuthAPIClient

from commerce_coordinator.apps.core.clients import Client

# Use special Celery logger for tasks client calls.
logger = get_task_logger(__name__)


class TitanAPIClient(Client):
    """
    API client for calls to Titan using API key.
    """

    def __init__(self):
        self.client = requests.Session()
        # Always send API key.
        self.client.headers.update(self.api_key_header)

    @property
    def api_base_url(self):
        """URL of API service."""
        return urljoin(settings.TITAN_URL, 'v1/')

    @property
    def api_key_header(self):
        """Header to add as API key for requests."""
        return {'X-API-Key': settings.TITAN_API_KEY}

    def post(self, resource_path, data):
        """
        Send a POST request to a Titan API resource.

        Arguments:
            resource_path: the path of the API resource to POST to
            data: the dictionary to send to the API resource
        Returns:
            dict: Dictionary represention of JSON returned from API

        """
        try:
            resource_url = urljoin(self.api_base_url, resource_path)
            response = self.client.post(
                resource_url,
                json=data,
                timeout=self.normal_timeout,
            )
            logger.debug("response: %s", response)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as exc:
            logger.error(exc)
            logger.debug("Request method: %s", exc.request.method)
            logger.debug("Request URL: %s", exc.request.url)
            logger.debug("Request headers: %s", exc.request.headers)
            logger.debug("Request body: %s", exc.request.body)
            raise

    def _request(self, request_method, resource_path, params=None, json=None):
        """
        Send a request to a Titan API resource.

        Arguments:
            request_method: method for the new :class:`Request` object.
            resource_path: the path of the API resource
            params: (optional) Dictionary or bytes to be sent in the query string for the :class:`Request`.
            json: (optional) json to send in the body of the :class:`Request`.
        Returns:
            dict: Dictionary representation of JSON returned from API

        """
        try:
            resource_url = urljoin(self.api_base_url, resource_path)
            response = self.client.request(
                method=request_method,
                url=resource_url,
                params=params,
                json=json,
                timeout=self.normal_timeout,
            )
            logger.debug('response status: %s', response.status_code)
            logger.debug('Request body: %s', response.request.body)
            response.raise_for_status()
            response_json = response.json()
            logger.debug('Response body: %s', response_json)
            return response_json
        except requests.exceptions.HTTPError as exc:
            logger.error(exc)
            logger.debug('Request method: %s', exc.request.method)
            logger.debug('Request URL: %s', exc.request.url)
            logger.debug('Request body: %s', exc.request.body)
            raise

    def create_order(self, edx_lms_user_id, email, product_sku, coupon_code):
        """
        API call to create a basket/order for a user in Titan.

        Args:
            coupon_code: A coupon code to initially apply to the order.
            edx_lms_user_id: The edx.org LMS user ID of the user receiving the order.
            email: The edx.org profile email of the user receiving the order. Required by Spree to create a user.
            product_sku: Array. An edx.org stock keeping units (SKUs) that the user would like to purchase.
        """
        return self._request(
            request_method='PUT',
            resource_path='order',
            json={
                'couponCode': coupon_code,
                'edxLmsUserId': edx_lms_user_id,
                'email': email,
                'productSku': product_sku,
            }
        )


class TitanOAuthAPIClient(TitanAPIClient):
    """
    API client for calls to Titan using OAuth bearer tokens.
    """

    def __init__(self):
        super().__init__()
        self.client = OAuthAPIClient(
            settings.TITAN_OAUTH2_PROVIDER_URL,
            self.oauth2_client_id,
            self.oauth2_client_secret,
            timeout=self.normal_timeout
        )
        # Always send API key.
        self.client.headers.update(self.api_key_header)

    @property
    def oauth2_client_id(self):
        """OAuth2 Titan client id."""
        return settings.TITAN_OAUTH2_KEY

    @property
    def oauth2_client_secret(self):
        """OAuth2 Titan client secret."""
        return settings.TITAN_OAUTH2_SECRET
