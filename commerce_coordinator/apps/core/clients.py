"""
API clients for services that manage orders.
"""
import logging

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
