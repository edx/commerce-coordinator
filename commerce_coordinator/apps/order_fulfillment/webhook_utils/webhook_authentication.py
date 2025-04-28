"""
This module provides authentication for incoming webhook requests using HMAC-SHA256 signature validation.
It includes the `HMACSignatureWebhookAuthentication` class, which ensures secure server-to-server communication.
"""

import base64
import hashlib
import hmac
import time

from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class HMACSignatureWebhookAuthentication(BaseAuthentication):
    """
    Authenticates incoming webhook requests using HMAC-SHA256 signature validation.
    This class expects two custom headers:
    - X-Fulfillment-Webhook-Timestamp: Unix timestamp of when the request was signed.
    - X-Fulfillment-Webhook-Signature: Base64-encoded HMAC-SHA256 signature of the request body.
    The request is authenticated by:
    - Verifying presence and validity of headers.
    - Ensuring the timestamp is within an acceptable time window to prevent replay attacks.
    - Recomputing the signature server-side and comparing it to the provided one.
    This is typically used for server-to-server webhook communication where a shared secret is configured.
    """

    MAX_TOLERANCE_SECONDS = 120  # 2 minutes

    def authenticate(self, request):
        timestamp = request.headers.get("X-Fulfillment-Webhook-Timestamp")
        signature = request.headers.get("X-Fulfillment-Webhook-Signature")

        if not timestamp or not signature:
            raise AuthenticationFailed("Missing required signature headers")

        try:
            timestamp_int = int(timestamp)
        except ValueError as exc:
            raise AuthenticationFailed("Invalid timestamp") from exc

        if abs(time.time() - timestamp_int) > self.MAX_TOLERANCE_SECONDS:
            raise AuthenticationFailed("Request too old")

        payload = request.body.decode()
        expected_signature = base64.b64encode(
            hmac.new(
                settings.FULFILLMENT_WEBHOOK_CUSTOM_SECRET,
                f"{timestamp}.{payload}".encode(),
                hashlib.sha256
            ).digest()
        ).decode()

        if not hmac.compare_digest(expected_signature, signature):
            raise AuthenticationFailed("Invalid signature")

        return None, None
