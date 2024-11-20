"""
API client logic shared between plugins.
"""
import logging
from urllib.parse import urljoin

from django.conf import settings
from edx_rest_api_client.client import OAuthAPIClient

logger = logging.getLogger(__name__)


def urljoin_directory(base_directory_url, relative_target_directory_url):
    """
    Adds relative_target_directory_url at the end of base_directory_url.

    Supports inconsistent trailing slashes and chaining outputs to inputs.

    A directory URL is one with an empty final path segment.

    See RFC 3986 for definition of a path segment and a relative-path
    reference.

    Args:
        base_directory_url: A directory URL, like
            "http://example.com/directory/".
        relative_target_directory_url: A relative-path reference of a
            directory URL, like "subdirectory/".

    Returns:
        String. The expanded URL of relative_target_directory_url when
        applied to base_directory_url.

        If base_directory_url is "http://example.com/directory/" and
        relative_target_directory_url is "subdirectory/", the returned
        string is "http://example.com/directory/subdirectory/".

        Will preserve both presence and absence of trailing slash in
        relative_target_directory_url.
    """
    # Add slash at end of base_directory_url so relative_target_directory_url won't overwrite last path segment.
    if not base_directory_url.endswith("/"):
        base_directory_url += "/"
    # Remove slash from start of relative_target_directory_url already present in base_directory_url.
    if relative_target_directory_url.startswith("/"):
        relative_target_directory_url = relative_target_directory_url[1:]
    return urljoin(base_directory_url, relative_target_directory_url)


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

    def log_request_response(self, ext_logger, response):
        """
        Log requests.Request responses with detailed information.

        Args:
            ext_logger: The logger of the module the Client (or Client-
                derived class) is running in.
            response: A successful Response object from the requests library.
        """
        # Extract request details and response information
        request_url = response.request.url
        request_body = response.request.body if response.request.body else 'N/A'
        request_headers = response.request.headers if response.request.headers else 'N/A'
        status_code = response.status_code
        response_body = response.text if response.text else 'N/A'

        # Log the detailed message
        ext_logger.debug(
            f"The API client call for url: {request_url} "
            f"with request_body: {request_body}, "
            f"request_headers: {request_headers} "
            f"was successful with status_code: {status_code}, "
            f"response_body: {response_body}"
        )

    def log_request_exception(self, ext_logger, exc):
        """
        Log requests.Request exceptions with detailed information.

        Args:
            ext_logger: The logger of the module the Client (or Client-
                derived class) is running in.
            exc: A RequestException object from the requests library.
        """
        # Extract request details and error information
        request_url = exc.request.url
        request_body = exc.request.body if exc.request.body else 'N/A'
        request_headers = exc.request.headers if exc.request.headers else 'N/A'
        status_code = exc.response.status_code if exc.response else 'N/A'
        response_body = exc.response.text if exc.response else 'N/A'

        # Log the detailed error message
        ext_logger.error(
            f"The API client call for url: {request_url} "
            f"with request_body: {request_body}, "
            f"request_headers: {request_headers} failed with "
            f"status_code: {status_code}, response_body: {response_body} "
            f"and error: {exc}"
        )


class BaseEdxOAuthClient(Client):
    """
    API client for calls to the other edX services.
    """

    def __init__(self):
        self.client = OAuthAPIClient(
            settings.BACKEND_SERVICE_EDX_OAUTH2_PROVIDER_URL.strip('/'),
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
