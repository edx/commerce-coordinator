"""
This module provides the `HMACWebhookCaller` class, which is responsible for securely
sending webhook requests with HMAC-based authentication. It includes functionality
for generating HMAC signatures, retrying failed requests with exponential backoff,
and logging request outcomes.
"""
import base64
import hashlib
import hmac
import json
import logging
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class HMACWebhookCaller:
    """
    Handles the creation and sending of HMAC-authenticated webhook requests.
    Includes retry logic with exponential backoff for failed requests.
    """
    MAX_RETRIES = 3
    BASE_BACKOFF = 1  # seconds

    def call(self, url: str, payload: dict):
        """
        Sends a webhook request to the specified URL with the given payload.

        Args:
            url (str): The webhook URL to send the request to.
            payload (dict): The payload to include in the webhook request.

        Returns:
            requests.Response: The response object if the request is successful.
            None: If all retry attempts fail.
        """
        payload_str = json.dumps(payload)
        timestamp = str(int(time.time()))
        signature = self._generate_signature(payload_str, timestamp)

        headers = {
            'X-Webhook-Timestamp': timestamp,
            'X-Webhook-Signature': signature,
            'Content-Type': 'application/json',
        }

        return self._make_request(url, payload_str, headers, 1)

    def _generate_signature(self, payload: str, timestamp: str) -> str:
        """
        Generates an HMAC signature for the given payload and timestamp.

        Args:
            payload (str): The JSON string of the payload.
            timestamp (str): The current timestamp.

        Returns:
            str: The base64-encoded HMAC signature.
        """
        message = f'{timestamp}.{payload}'.encode()
        return base64.b64encode(
            hmac.new(settings.FULFILLMENT_WEBHOOK_CUSTOM_SECRET, message, hashlib.sha256).digest()
        ).decode()

    def _make_request(self, url, payload_str, headers, attempt_number):
        """
        Makes an HTTP POST request to the specified URL with retry logic.

        Args:
            url (str): The webhook URL to send the request to.
            payload_str (str): The JSON string of the payload.
            headers (dict): The headers to include in the request.
            attempt_number (int): The current attempt number.

        Returns:
            requests.Response: The response object if the request is successful.
            None: If all retry attempts fail.
        """
        try:
            response = requests.post(url, headers=headers, data=payload_str, timeout=5)
            response.raise_for_status()
            return response

        except requests.RequestException as err:
            if attempt_number >= self.MAX_RETRIES:
                logger.error("[Fulfillment Webhook] Final attempt #%s failed for URL: %s with error: %s",
                             attempt_number, url, err)
                return None

            next_backoff = self.BASE_BACKOFF * attempt_number
            logger.warning("[Fulfillment Webhook] Attempt #%s failed. Retrying in %s seconds...",
                           attempt_number, next_backoff)
            time.sleep(next_backoff)
            return self._make_request(url, payload_str, headers, attempt_number + 1)
