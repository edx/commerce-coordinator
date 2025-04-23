import time
import json
import hmac
import hashlib
import base64
import requests
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class HMACWebhookCaller:
    MAX_RETRIES = 3
    BASE_BACKOFF = 1  # seconds

    def call(self, url: str, payload: dict):
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
        message = f'{timestamp}.{payload}'.encode()
        return base64.b64encode(
            hmac.new(settings.FULFILLMENT_WEBHOOK_CUSTOM_SECRET, message, hashlib.sha256).digest()
        ).decode()

    def _make_request(self, url, payload_str, headers, attempt_number):
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
