"""
Views for the commercetools app
"""
import logging
import hmac, hashlib, base64
import requests
import time
import json

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.http import JsonResponse
from rest_framework import status
from rest_framework.response import Response

from commerce_coordinator.apps.core.views import SingleInvocationAPIView

logger = logging.getLogger(__name__)

def make_webhook_call(url: str, payload: dict):
    MAX_RETRIES = 3
    BASE_BACKOFF = 1  # seconds

    def generate_signature(payload: str, timestamp: str) -> str:
        message = f'{timestamp}.{payload}'.encode()
        return base64.b64encode(
            hmac.new(settings.FULFILLMENT_WEBHOOK_CUSTOM_SECRET, message, hashlib.sha256).digest()
        ).decode()

    payload_str = json.dumps(payload)
    # timestamp = str(int(time.time()) - (5 * 3600)) # error scenario
    timestamp = str(int(time.time()))
    signature = generate_signature(payload_str, timestamp)

    headers = {
        'X-Webhook-Timestamp': timestamp,
        'X-Webhook-Signature': signature,
        'Content-Type': 'application/json',
    }

    def attempt(attempt_number: int):
        try:
            response = requests.post(url, headers=headers, data=payload_str, timeout=10)
            response.raise_for_status()
            return response

        except requests.RequestException as err:
            if attempt_number >= MAX_RETRIES:
                logger.error(
                    "[Webhook] Final attempt #%s failed for URL: %s with error: %s",
                    attempt_number, url, err
                )
                return None

            next_attempt = attempt_number + 1
            next_backoff = BASE_BACKOFF * next_attempt

            logger.warning(
                "[Webhook] Attempt #%s failed for URL: %s | error: %s. Retrying in %s seconds...",
                attempt_number, url, err, next_backoff
            )
            time.sleep(next_backoff)
            return attempt(next_attempt)

    return attempt(1)


class TriggerOrderFulfillmentCustom(SingleInvocationAPIView):
    """Order Fulfillment View"""

    def get(self, request):
        """Receive a message from commercetools forwarded by aws event bridge"""

        tag = type(self).__name__

        logger.info(f'[CT-{tag}] Message received to trigger fulfillment - Custom.')

        url = 'http://localhost:8155/fulfill-custom/'
        payload = {
            "order_id": "1234",
        }
        response = make_webhook_call(url, payload)

        if response and response.status_code == 200:
            logger.info(f"[CT-{tag}] Custom Webhook call done. Response: {response.status_code} - {response.text}")
            return Response(status=status.HTTP_200_OK)
        else:
            logger.warning(f"[CT-{tag}] Custom Webhook call failed.")
            return Response(status=status.HTTP_503_SERVICE_UNAVAILABLE)

MAX_TOLERANCE_SECONDS = 300  # 5 minutes

class OrderFulfillmentResponseCustom(SingleInvocationAPIView):
    """Order Fulfillment View"""

    def verify_signature(self, payload, timestamp, received_signature):
        expected_signature = base64.b64encode(
            hmac.new(
                settings.FULFILLMENT_WEBHOOK_CUSTOM_SECRET,
                f"{timestamp}.{payload}".encode(),
                hashlib.sha256
            ).digest()
        ).decode()

        return hmac.compare_digest(expected_signature, received_signature)

    def is_authorized_webhook_request(self, request):
        timestamp = request.headers.get("X-Webhook-Timestamp")
        signature = request.headers.get("X-Webhook-Signature")
        body = request.body.decode()
        print('\n\n\nrequest body', body)

        if not timestamp or not signature:
            return False, {'error': 'Missing headers', 'status': 400}

        # Check timestamp freshness
        if abs(time.time() - int(timestamp)) > MAX_TOLERANCE_SECONDS:
            return False, {'error': 'Request too old', 'status': 403}

        if not self.verify_signature(body, timestamp, signature):
            return False, {'error': 'Invalid signature', 'status': 403}

        return True, None

    def post(self, request):
        """Receive a message from commercetools forwarded by aws event bridge"""
        print('\n\n\nrequest headers', request.headers)
        is_valid, error_response = self.is_authorized_webhook_request(request)
        if not is_valid:
            return JsonResponse({'error': error_response.get('error')}, status=error_response.get('status'))

        print('\n\n\nrequest data', request.data)

        print('\n\n\n\n Hello, Custom - Order Fulfillment Response received!')
        return Response(status=200)
