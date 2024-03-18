"""Tests for the commercetools views"""

from django.conf import settings
from django.test import RequestFactory
from rest_framework.test import APITestCase
from rest_framework_jwt.authentication import JSONWebTokenAuthentication

from commerce_coordinator.apps.core.models import User

from ..authentication import JwtBearerAuthentication


class JwtBearerAuthenticationTests(APITestCase):
    "Tests for JwtBearerAuthentication class."

    uut = JwtBearerAuthentication

    test_username = 'username'
    test_password = 'password'

    def setUp(self):
        """Create test user and token."""
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username=self.test_username,
            password=self.test_password
        )
        self.payload = JSONWebTokenAuthentication.jwt_create_payload(self.user)
        self.token = JSONWebTokenAuthentication.jwt_encode_payload(self.payload)

    def test_authenticated_with_bearer_prefix(self):
        """
        Check user with valid credentials passed using Bearer auth header prefix
        is authenticated.
        """

        # Assume:
        assert settings.JWT_AUTH['JWT_AUTH_HEADER_PREFIX'] == 'JWT'

        # Build request:
        request = self.factory.post(
            '/test',
            headers={'Authorization': f'Bearer {self.token}'}
        )

        # Authenticate:
        result = self.uut().authenticate(request)
        # See base implementation:
        # https://github.com/Styria-Digital/django-rest-framework-jwt/blob/4e8550e15902399df277aac97e6f300a0610697f/src/rest_framework_jwt/authentication.py#L60

        # A return of a user, token tuple means the user is authenticated.
        assert result == (self.user, self.token)

    def test_not_authenticated_with_jwt_prefix(self):
        """
        Check user with valid credentials passed using JWT auth header prefix
        is not authenticated.

        Why: The point of this class / the unit under test is to force the
        equivalent of overriding JWT_AUTH_HEADER_PREFIX to ``Bearer``.
        """

        # Assume:
        assert settings.JWT_AUTH['JWT_AUTH_HEADER_PREFIX'] == 'JWT'

        # Build request:
        request = self.factory.post(
            '/test',
            headers={'Authorization': f'JWT {self.token}'}
        )

        # Authenticate:
        result = self.uut().authenticate(request)
        # See base implementation:
        # https://github.com/Styria-Digital/django-rest-framework-jwt/blob/4e8550e15902399df277aac97e6f300a0610697f/src/rest_framework_jwt/authentication.py#L60

        # A return of None means the user is not authenticated.
        assert result is None
