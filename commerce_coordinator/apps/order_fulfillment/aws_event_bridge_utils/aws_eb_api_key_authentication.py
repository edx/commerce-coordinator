"""
This module contains the `AWSAPIKeyAuthentication` class, which provides
authentication for API requests using API keys stored in AWS Secrets Manager.
"""

import json
import time
import boto3
from botocore.exceptions import ClientError

from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class AWSAPIKeyAuthentication(BaseAuthentication):
    """
    Authentication class that validates API requests using API keys stored in AWS Secrets Manager.

    This class fetches the API key configuration from AWS Secrets Manager and caches it in-memory
    for a configurable time-to-live (TTL) to avoid repeated fetches on each request.

    Attributes:
        _cached_secret (dict): Cached secret containing API key configuration.
        _cache_timestamp (float): Timestamp of when the secret was last fetched.
        _CACHE_TTL_SECONDS (int): Time-to-live for the cached secret in seconds.
    """
    _cached_secret = None
    _cache_timestamp = None
    _CACHE_TTL_SECONDS = 300

    @classmethod
    def get_secret(cls):
        """
        Retrieves the API key configuration from AWS Secrets Manager.

        Uses caching to avoid repeated requests to AWS Secrets Manager within the TTL.

        Returns:
            dict: API key configuration containing `api_key_name` and `api_key_value`.

        Raises:
            AuthenticationFailed: If the secret cannot be fetched or is invalid.
        """
        time_now = time.time()

        if (
            cls._cached_secret is not None and
            cls._cache_timestamp is not None and
            time_now - cls._cache_timestamp < cls._CACHE_TTL_SECONDS
        ):
            return cls._cached_secret

        secret_name = settings.AWS_ORDER_FULFILLMENT_SECRET_NAME
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )

        try:
            response = client.get_secret_value(SecretId=secret_name)
        except ClientError as err:
            raise AuthenticationFailed(f"Unable to fetch AWS secret: {err}")

        try:
            secret = json.loads(response['SecretString'])
        except (KeyError, json.JSONDecodeError) as err:
            raise AuthenticationFailed(f"Invalid secret format: {err}")

        cls._cached_secret = secret
        cls._cache_timestamp = time_now
        return secret

    def authenticate(self, request):
        """
        Authenticates the incoming request using the API key configuration.

        Args:
            request (Request): The incoming HTTP request.

        Returns:
            tuple: A tuple of `(None, None)` if authentication is successful.

        Raises:
            AuthenticationFailed: If the API key is invalid or missing.
        """
        secret = self.get_secret()
        api_key_name = secret.get('api_key_name')
        api_key_value = secret.get('api_key_value')

        if not api_key_name or not api_key_value:
            raise AuthenticationFailed("API key configuration is incomplete")

        received_api_key = request.headers.get(api_key_name)
        if not received_api_key or received_api_key != api_key_value:
            raise AuthenticationFailed("Invalid or missing API key")

        return None, None
