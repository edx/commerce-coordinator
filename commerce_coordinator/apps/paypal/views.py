"""
Paypal app views
"""

import base64
import logging
from urllib.parse import urlparse
import zlib

import requests
from cryptography import x509
from rest_framework.permissions import AllowAny
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from commerce_coordinator.apps.core.views import SingleInvocationAPIView
from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient

from commerce_coordinator.apps.paypal.signals import payment_refunded_signal

from .models import KeyValueCache


logger = logging.getLogger(__name__)


class PayPalWebhookView(SingleInvocationAPIView):
    """
    PayPal webhook view
    """
    ALLOWED_DOMAINS = ['www.paypal.com', 'api.paypal.com', 'api.sandbox.paypal.com', 'www.sandbox.paypal.com']
    http_method_names = ["post"]
    authentication_classes = []
    permission_classes = [AllowAny]

    def _get_certificate(self, url):
        """
        Get certificate from the given URL
        """
        if not self._is_valid_url(url):
            raise ValueError("Invalid or untrusted URL provided")
        try:
            cache = KeyValueCache.objects.get(cache_key=url)
            return cache.value
        except KeyValueCache.DoesNotExist:
            r = requests.get(url)  # pylint: disable=missing-timeout
            KeyValueCache.objects.create(cache_key=url, cache_value=r.text)
            return r.text

    def _is_valid_url(self, url):
        """
        Check if the given URL is valid
        """
        try:
            parsed_url = urlparse(url)
            if parsed_url.scheme not in ['http', 'https']:
                return False
            if parsed_url.netloc not in self.ALLOWED_DOMAINS:
                return False
            return True
        except Exception:  # pylint: disable=broad-exception-caught
            return False

    def post(self, request):
        """
        Handle POST request
        """
        tag = type(self).__name__
        body = request.body

        transmission_id = request.headers.get("paypal-transmission-id")
        if self._is_running(tag, transmission_id):  # pragma no cover
            self.meta_should_mark_not_running = False
            return Response(status=status.HTTP_200_OK)
        else:
            self.mark_running(tag, transmission_id)

        timestamp = request.headers.get("paypal-transmission-time")
        crc = zlib.crc32(body)
        webhook_id = settings.PAYPAL_WEBHOOK_ID
        message = f"{transmission_id}|{timestamp}|{webhook_id}|{crc}"

        signature = base64.b64decode(request.headers.get("paypal-transmission-sig"))

        certificate = self._get_certificate(request.headers.get("paypal-cert-url"))
        cert = x509.load_pem_x509_certificate(
            certificate.encode("utf-8"), default_backend()
        )
        public_key = cert.public_key()

        try:
            # TODO: In future we can move this logic over to redis to avoid hitting the database
            public_key.verify(
                signature, message.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256()
            )
        except Exception:  # pylint: disable=broad-exception-caught
            return Response(status=status.HTTP_400_BAD_REQUEST)

        if request.data.get("event_type") == "PAYMENT.CAPTURE.REFUNDED":
            twou_order_number = request.data.get("resource").get("invoice_id", None)
            capture_url = request.data.get("resource").get("links", [])
            capture_id = None
            for link in capture_url:
                if link.get("rel") == "up" and "captures" in link.get("href"):
                    capture_id = link.get("href").split("/")[-1]
                    break
            ct_api_client = CommercetoolsAPIClient()
            payment = ct_api_client.get_payment_by_transaction_interaction_id(
                capture_id
            )
            paypal_order_id = payment.key

            logger.info(
                "[Paypal webhooks] refund event %s with order_number [%s], paypal_order_id [%s] received",
                request.data.get("event_type"),
                twou_order_number,
                paypal_order_id,
            )

            refund = {
                "id": request.data.get("resource").get("id"),
                "created": request.data.get("resource").get("create_time"),
                "status": request.data.get("resource").get("status"),
                "amount": request.data.get("resource").get("amount").get("value"),
                "currency": request.data.get("resource").get("amount").get("currency_code"),
            }

            payment_refunded_signal.send_robust(
                sender=self.__class__, paypal_order_id=paypal_order_id, refund=refund
            )

        return Response(status=status.HTTP_200_OK)
