"""
Google push subscription authentication test class.
"""

from unittest.mock import patch

from django.test import RequestFactory, TestCase
from rest_framework.exceptions import AuthenticationFailed

from commerce_coordinator.apps.iap.authentication import GoogleSubscriptionAuthentication


class GoogleSubscriptionAuthenticationTests(TestCase):
    """
    Unit tests for the GoogleSubscriptionAuthentication class which verifies
    Google-signed JWTs sent in Authorization headers of Pub/Sub push requests.
    """

    def setUp(self):
        """
        Initializes the test environment with a request factory and an instance
        of the authentication class.
        """

        self.factory = RequestFactory()
        self.auth = GoogleSubscriptionAuthentication()

    def _request_with_auth(self, token):
        """
        Returns a POST request with the given token set in the Authorization header.

        Args:
            token (str): The JWT to attach to the request.

        Returns:
            HttpRequest: A Django request object with the Authorization header.
        """

        request = self.factory.post("/test-url/")
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        return request

    def test_missing_authorization_header(self):
        """
        Raises AuthenticationFailed if no Authorization header is present.

        Expects:
            AuthenticationFailed with "Missing or invalid Authorization header".
        """

        request = self.factory.post("/test-url/")
        with self.assertRaises(AuthenticationFailed) as ctx:
            self.auth.authenticate(request)
        self.assertIn("Missing or invalid Authorization header", str(ctx.exception))

    def test_malformed_authorization_header(self):
        """
        Raises AuthenticationFailed if Authorization header does not start with 'Bearer '.

        Expects:
            AuthenticationFailed with "Missing or invalid Authorization header".
        """

        request = self.factory.post("/test-url/")
        request.META["HTTP_AUTHORIZATION"] = "Token bad.header"
        with self.assertRaises(AuthenticationFailed) as ctx:
            self.auth.authenticate(request)
        self.assertIn("Missing or invalid Authorization header", str(ctx.exception))

    @patch("commerce_coordinator.apps.iap.authentication.id_token.verify_oauth2_token")
    def test_invalid_token_raises_authentication_failed(self, mock_verify):
        """
        Raises AuthenticationFailed if token verification fails using Google's verifier.

        Mocks:
            id_token.verify_oauth2_token to raise ValueError.

        Expects:
            AuthenticationFailed with "JWT verification failed: ..."
        """

        mock_verify.side_effect = ValueError("Token verification failed")
        request = self._request_with_auth("fake.token.value")

        with self.assertRaises(AuthenticationFailed) as ctx:
            self.auth.authenticate(request)

        self.assertIn("JWT verification failed: Token verification failed", str(ctx.exception))
        mock_verify.assert_called_once()

    @patch("commerce_coordinator.apps.iap.authentication.id_token.verify_oauth2_token")
    def test_valid_token_returns_none(self, mock_verify):
        """
        Successfully authenticates when a valid token is provided.

        Mocks:
            id_token.verify_oauth2_token to return a decoded token.

        Returns:
            Tuple[None, None]: No user or token is attached, only verification occurs.
        """

        mock_verify.return_value = {
            "sub": "123456789",
            "email": "user@test.com"
        }
        request = self._request_with_auth("valid.token.here")

        user, auth_token = self.auth.authenticate(request)

        self.assertIsNone(user)
        self.assertIsNone(auth_token)
        mock_verify.assert_called_once()
