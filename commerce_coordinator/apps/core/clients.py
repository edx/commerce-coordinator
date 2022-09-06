"""
API client logic shared between plugins.
"""
import logging

from django.conf import settings
from edx_rest_api_client.client import OAuthAPIClient

logger = logging.getLogger(__name__)


class Client:
    """
    Base class for API clients.
    """

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


class BaseEdxOAuthClient(Client):
    """
    API client for calls to the other edX services.
    """

    def __init__(self):
        self.client = OAuthAPIClient(
            settings.SOCIAL_AUTH_EDX_OAUTH2_URL_ROOT.strip('/'),
            self.oauth2_client_id,
            self.oauth2_client_secret,
            timeout=self.normal_timeout
        )

    @property
    def oauth2_client_id(self):
        return settings.BACKEND_SERVICE_EDX_OAUTH2_KEY

    @property
    def oauth2_client_secret(self):
        return settings.BACKEND_SERVICE_EDX_OAUTH2_SECRET
