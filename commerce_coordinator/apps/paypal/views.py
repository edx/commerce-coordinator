"""
Paypal app views
"""

import base64
import logging
import zlib
from urllib.parse import urlparse

import requests
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from commerce_coordinator.apps.core.views import SingleInvocationAPIView
from commerce_coordinator.apps.paypal.signals import payment_refunded_signal

logger = logging.getLogger(__name__)

WEBHOOK_ID = settings.PAYMENT_PROCESSOR_CONFIG['edx']['paypal']['paypal_webhook_id']


class PayPalWebhookView(SingleInvocationAPIView):
    """
    PayPal webhook view
    """
    ALLOWED_DOMAINS = ['www.paypal.com', 'api.paypal.com', 'api.sandbox.paypal.com', 'www.sandbox.paypal.com']
    http_method_names = ["post"]
    authentication_classes = []
    permission_classes = [AllowAny]
    # TODO: Limit the view to our paypal webhook servers only and remove throttling
    throttle_classes = [UserRateThrottle]

    def _get_certificate(self, url):
        """
        Get certificate from the given URL
        """
        if not self._is_valid_url(url):
            raise ValueError("Invalid or untrusted URL provided")
        r = requests.get(url)  # pylint: disable=missing-timeout
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
        body = request.body
        tag = type(self).__name__
        twou_order_number = request.data.get("resource").get("invoice_id", None)
        event_type = request.data.get("event_type")
        webhook_id = WEBHOOK_ID

        transmission_id = request.headers.get("paypal-transmission-id")
        timestamp = request.headers.get("paypal-transmission-time")
        crc = zlib.crc32(body)

        message = f"{transmission_id}|{timestamp}|{webhook_id}|{crc}"
        signature = base64.b64decode(request.headers.get("paypal-transmission-sig"))
        certificate = self._get_certificate(request.headers.get("paypal-cert-url"))
        cert = x509.load_pem_x509_certificate(
            certificate.encode("utf-8"), default_backend()
        )
        public_key = cert.public_key()

        try:
            public_key.verify(
                signature, message.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256()
            )
        except Exception as error:  # pylint: disable=broad-exception-caught
            logger.exception("Encountered exception %s verifying paypal certificate for ct_order: %s for event %s",
                             error,
                             twou_order_number,
                             event_type)
            return Response(status=status.HTTP_400_BAD_REQUEST)

        if event_type == "PAYMENT.CAPTURE.REFUNDED":
            refund_id = request.data.get("resource").get("id")
            if self._is_running(tag, refund_id):  # pragma no cover
                self.meta_should_mark_not_running = False
                return Response(status=status.HTTP_200_OK)
            else:
                self.mark_running(tag, refund_id)
            refund_urls = request.data.get("resource").get("links", [])
            paypal_capture_id = None
            # Getting the capture ID from the links in the refund event as it is not
            # present in the payload and is required for initiating the refund.
            for link in refund_urls:
                if link.get("rel") == "up" and "captures" in link.get("href"):
                    paypal_capture_id = link.get("href").split("/")[-1]
                    break

            logger.info(
                "[Paypal webhooks] refund event %s with order_number %s, paypal_capture_id %s received",
                event_type,
                twou_order_number,
                paypal_capture_id,
            )

            refund = {
                "id": refund_id,
                "created": request.data.get("resource").get("create_time"),
                "status": request.data.get("resource").get("status"),
                "amount": request.data.get("resource").get("amount").get("value"),
                "currency": request.data.get("resource").get("amount").get("currency_code"),
            }

            payment_refunded_signal.send_robust(
                sender=self.__class__, paypal_capture_id=paypal_capture_id, refund=refund
            )
        else:
            logger.info(
                "[Paypal webhooks] Unhandled Paypal event %s received with payload %s",
                event_type,
                request.data,
            )

        return Response(status=status.HTTP_200_OK)
