"""
API clients for Titan.
"""

import requests
from celery.utils.log import get_task_logger
from django.conf import settings
from edx_rest_api_client.client import OAuthAPIClient

# Use special Celery logger for tasks client calls.
logger = get_task_logger(__name__)


class TitanAPIClient():
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
        return str(settings.TITAN_URL).strip('/') + '/v1'

    @property
    def api_key_header(self):
        """Header to add to all API requests to authenticate to endpoint."""
        return {'X-API-Key': settings.TITAN_API_KEY}

    @property
    def normal_timeout(self):
        """
        Shortcut for a normal timeout. Must be manually applied to each request.

        See https://requests.readthedocs.io/en/latest/user/quickstart/#timeouts.
        """
        return (
            settings.REQUEST_CONNECT_TIMEOUT_SECONDS,
            settings.REQUEST_READ_TIMEOUT_SECONDS
        )

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
            resource_url = self.api_base_url.strip('/') + resource_path
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
            timeout=(
                settings.REQUEST_CONNECT_TIMEOUT_SECONDS,
                settings.REQUEST_READ_TIMEOUT_SECONDS
            )
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
