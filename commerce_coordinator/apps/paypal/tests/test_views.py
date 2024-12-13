"""
Paypal views test cases
"""
import base64
import zlib
from unittest.mock import patch, MagicMock

from django.conf import settings
from django.urls import reverse
from rest_framework.test import APITestCase

from commerce_coordinator.apps.paypal.views import PayPalWebhookView


class PayPalWebhookViewTests(APITestCase):
    """ Tests for PayPalWebhookView """

    def setUp(self):
        super().setUp()
        self.url = reverse('paypal:paypal_webhook')
        self.headers = {
            'paypal-transmission-id': 'test-transmission-id',
            'paypal-transmission-time': '2023-01-01T00:00:00Z',
            'paypal-transmission-sig': base64.b64encode(b'test-signature').decode('utf-8'),
            'paypal-cert-url': 'https://www.paypal.com/cert.pem',
        }
        self.body = b'test-body'
        self.crc = zlib.crc32(self.body)
        self.message = (
            f"{self.headers['paypal-transmission-id']}|{self.headers['paypal-transmission-time']}|"
            f"{settings.PAYPAL_WEBHOOK_ID}|{self.crc}"
        )

    @patch('requests.get')
    @patch('commerce_coordinator.apps.paypal.views.x509.load_pem_x509_certificate')
    def test_post_refund_event(self, mock_load_cert, mock_requests_get):
        mock_requests_get.return_value.text = 'test-cert'
        mock_load_cert.return_value.public_key.return_value.verify = MagicMock()

        data = {
            "event_type": "PAYMENT.CAPTURE.REFUNDED",
            "resource": {
                "id": "test-refund-id",
                "create_time": "2023-01-01T00:00:00Z",
                "status": "COMPLETED",
                "amount": {
                    "value": "100.00",
                    "currency_code": "USD"
                },
                "invoice_id": "test-order-number",
                "links": [
                    {"rel": "up", "href": "https://api.paypal.com/v2/payments/captures/test-capture-id"}
                ]
            }
        }

        response = self.client.post(self.url, data, format='json', headers=self.headers)
        self.assertEqual(response.status_code, 200)

    @patch('requests.get')
    @patch('commerce_coordinator.apps.paypal.views.x509.load_pem_x509_certificate')
    def test_post_invalid_signature(self, mock_load_cert, mock_requests_get):
        mock_requests_get.return_value.text = 'test-cert'
        mock_load_cert.return_value.public_key.return_value.verify.side_effect = Exception("Invalid signature")

        data = {
            "event_type": "PAYMENT.CAPTURE.REFUNDED",
            "resource": {}
        }

        response = self.client.post(self.url, data, format='json', headers=self.headers)
        self.assertEqual(response.status_code, 400)

    @patch('requests.get')
    def test_get_certificate_from_url(self, mock_requests_get):
        mock_requests_get.return_value.text = 'test-cert'
        view = PayPalWebhookView()
        cert = view._get_certificate(self.headers['paypal-cert-url'])  # pylint: disable=protected-access
        self.assertEqual(cert, 'test-cert')
        mock_requests_get.assert_called_once_with(self.headers['paypal-cert-url'])

    def test_is_valid_url(self):
        view = PayPalWebhookView()
        self.assertTrue(view._is_valid_url('https://www.paypal.com/cert.pem'))  # pylint: disable=protected-access
        self.assertFalse(view._is_valid_url('ftp://www.paypal.com/cert.pem'))  # pylint: disable=protected-access
        self.assertFalse(view._is_valid_url('https://www.untrusted.com/cert.pem'))  # pylint: disable=protected-access

    @patch('requests.get')
    @patch('commerce_coordinator.apps.paypal.views.x509.load_pem_x509_certificate')
    def test_invalid_event_type(self, mock_load_cert, mock_requests_get):
        mock_requests_get.return_value.text = 'test-cert'
        mock_load_cert.return_value.public_key.return_value.verify = MagicMock()

        data = {
            "event_type": "INVALID.EVENT.TYPE",
            "resource": {}
        }

        response = self.client.post(self.url, data, format='json', headers=self.headers)
        self.assertEqual(response.status_code, 200)
