"""
Google push subscription authentication class.
"""
import logging

from django.conf import settings
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

logger = logging.getLogger(__name__)


class GoogleSubscriptionAuthentication(BaseAuthentication):
    """
    Authentication class for verifying JWT tokens sent by Google Pub/Sub push requests.

    This authentication class extracts the Bearer token from the Authorization header
    and verifies it using Google's OAuth2 token verifier. If the token is missing,
    invalid, or verification fails, an AuthenticationFailed exception is raised.

    Returns:
        Tuple[None, None]: If authentication succeeds. No user or auth object is attached,
        as this authentication is only used to verify request validity, not to associate users.

    Raises:
        AuthenticationFailed: If the Authorization header is missing, malformed, or the JWT is invalid.
    """
    def authenticate(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION")

        if not auth_header or not auth_header.startswith("Bearer "):
            logger.error('Failed [GoogleSubscriptionAuthentication] Missing or invalid Authorization header')
            raise AuthenticationFailed("Missing or invalid Authorization header")

        token = auth_header.split("Bearer ")[1]

        try:
            request_adapter = google_requests.Request()
            id_token.verify_oauth2_token(
                token,
                request_adapter,
                audience=settings.PAYMENT_PROCESSOR_CONFIG['edx']['android_iap']['google_auth_aud_key']
            )

        except Exception as e:
            error_msg = str(e)

            if "Token has wrong audience" in error_msg and "expected one of" in error_msg:
                parsed_error_msg = error_msg.split("expected one of")[0].strip().rstrip(",")
            else:
                parsed_error_msg = error_msg

            logger.error('Failed [GoogleSubscriptionAuthentication]'
                         f'JWT verification failed with error {parsed_error_msg}')
            raise AuthenticationFailed(f"JWT verification failed: {parsed_error_msg}") from e

        return (None, None)
