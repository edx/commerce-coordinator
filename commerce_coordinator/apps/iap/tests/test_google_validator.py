"""
Google Play Validator Test Module

This module contains tests for the GooglePlayValidator used for validating Google Play in-app purchase receipts.
It mocks the Google Play API client and tests both success and failure scenarios for validation.
"""

import unittest
from unittest import mock

from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings
from googleapiclient.errors import HttpError

from commerce_coordinator.apps.iap.google_validator import GooglePlayValidator, get_consumable_android_sku

VALID_PURCHASE_TOKEN = "valid.purchase.token"
INVALID_PURCHASE_TOKEN = "invalid.purchase.token"
PRICE = 10

MOCK_PAYMENT_PROCESSOR_CONFIG = {
    'edx': {
        'android_iap': {
            'google_bundle_id': 'com.example.app',
            'google_service_account_key_file': '{"key": "value"}'
        }
    }
}


class GooglePlayValidatorTests(unittest.TestCase):
    """Tests for GooglePlayValidator."""

    def setUp(self):
        self.validator = GooglePlayValidator()

    @override_settings(PAYMENT_PROCESSOR_CONFIG=MOCK_PAYMENT_PROCESSOR_CONFIG)
    @mock.patch("commerce_coordinator.apps.iap.google_validator.build")
    @mock.patch("google.oauth2.service_account.Credentials.from_service_account_info")
    def test_validate_success(self, _, mock_build):
        # Mock the nested API call chain: purchases().products().get().execute()
        mock_service = mock.Mock()
        mock_request = mock.Mock()
        mock_request.execute.return_value = {
            "purchaseState": 0  # Purchased
        }
        mock_service.purchases().products().get.return_value = mock_request
        mock_build.return_value = mock_service

        result = self.validator.validate(VALID_PURCHASE_TOKEN, PRICE)

        self.assertIn("raw_response", result)
        self.assertFalse(result["is_canceled"])
        self.assertFalse(result["is_expired"])

    @override_settings(PAYMENT_PROCESSOR_CONFIG=MOCK_PAYMENT_PROCESSOR_CONFIG)
    @mock.patch("commerce_coordinator.apps.iap.google_validator.build")
    @mock.patch("google.oauth2.service_account.Credentials.from_service_account_info")
    def test_validate_http_error(self, _, mock_build):
        mock_service = mock.Mock()
        mock_build.return_value = mock_service

        # Simulate HttpError on .execute()
        http_error = HttpError(resp=mock.Mock(status=400), content=b"Bad Request")
        mock_service.purchases().products().get.side_effect = http_error

        result = self.validator.validate(INVALID_PURCHASE_TOKEN, PRICE)
        self.assertIn("error", result)
        self.assertIn("message", result)

    @override_settings(PAYMENT_PROCESSOR_CONFIG=MOCK_PAYMENT_PROCESSOR_CONFIG)
    @mock.patch("commerce_coordinator.apps.iap.google_validator.build", side_effect=Exception("Unexpected"))
    @mock.patch("google.oauth2.service_account.Credentials.from_service_account_info")
    def test_validate_unexpected_error(self, _, _mock_build):
        result = self.validator.validate(VALID_PURCHASE_TOKEN, PRICE)
        self.assertIn("error", result)
        self.assertEqual(result["message"], "Unexpected error occurred")

    @override_settings(PAYMENT_PROCESSOR_CONFIG={'edx': {'android_iap': {}}})
    def test_missing_configuration(self):
        with self.assertRaises(ImproperlyConfigured):
            self.validator.validate(VALID_PURCHASE_TOKEN, PRICE)

    def test_get_consumable_android_sku(self):
        self.assertEqual(get_consumable_android_sku(5), "mobile.android.usd5")
        self.assertEqual(get_consumable_android_sku(12), "mobile.android.usd12")
