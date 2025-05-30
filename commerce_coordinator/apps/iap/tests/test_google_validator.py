"""
Google Play Validator Test Module

This module contains tests for the GooglePlayValidator used for validating Google Play in-app purchase receipts.
It mocks the GooglePlayVerifier and tests both success and failure scenarios for validation.
"""

import unittest
from unittest import mock

from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings
from inapppy import errors
from testfixtures import LogCapture

from commerce_coordinator.apps.iap.google_validator import GooglePlayValidator

VALID_PURCHASE_TOKEN = "test.purchase.token"
INVALID_PURCHASE_TOKEN = "test.purchase.invalid_token"

MOCK_PAYMENT_PROCESSOR_CONFIG = {
    'android_iap': {
        'google_bundle_id': 'test.google.bundle.id',
        'google_service_account_key_file': 'test.key.file'
    }
}


class GooglePlayVerifierResponse:
    """Mock response object for GooglePlayVerifier."""

    def __init__(self):
        self.raw_response = '{}'
        self.is_canceled = False
        self.is_expired = False


class GooglePlayVerifierProxy:
    """Mock proxy for inapppy.GooglePlayVerifier."""

    def verify_with_result(self, purchase_token, product_sku, is_subscription=False):  # pylint: disable=unused-argument
        if purchase_token == INVALID_PURCHASE_TOKEN:
            raise errors.GoogleError("Invalid purchase token.")
        return GooglePlayVerifierResponse()


class GoogleValidatorTests(unittest.TestCase):
    """Tests for GooglePlayValidator."""

    PRODUCT_SKU = "test.product.sku"

    def setUp(self):
        self.validator = GooglePlayValidator()

    @override_settings(
        PAYMENT_PROCESSOR_CONFIG=MOCK_PAYMENT_PROCESSOR_CONFIG,
    )
    @mock.patch('commerce_coordinator.apps.iap.google_validator.GooglePlayVerifier')
    def test_validate_successful(self, mock_google_verifier):
        mock_google_verifier.return_value = GooglePlayVerifierProxy()
        response = self.validator.validate(VALID_PURCHASE_TOKEN, self.PRODUCT_SKU)
        self.assertEqual(response["raw_response"], "{}")
        self.assertFalse(response["is_canceled"])
        self.assertFalse(response["is_expired"])

    @override_settings(
        PAYMENT_PROCESSOR_CONFIG=MOCK_PAYMENT_PROCESSOR_CONFIG,
    )
    @mock.patch('commerce_coordinator.apps.iap.google_validator.GooglePlayVerifier')
    def test_validate_failure(self, mock_google_verifier):
        mock_google_verifier.return_value = GooglePlayVerifierProxy()
        logger_name = 'commerce_coordinator.apps.iap.google_validator'

        with LogCapture(logger_name) as google_validator_log_capture:
            response = self.validator.validate(INVALID_PURCHASE_TOKEN, self.PRODUCT_SKU)

            google_validator_log_capture.check_present(
                (logger_name, 'ERROR', "Google Play validation failed: GoogleError Invalid purchase token. None"),
            )

            self.assertIn('error', response)
            self.assertEqual(response['error'], 'GoogleError Invalid purchase token. None')

    @override_settings(
        PAYMENT_PROCESSOR_CONFIG={'android_iap': {}},
        google_service_account_key_file=None
    )
    def test_missing_configuration(self):
        with self.assertRaises(ImproperlyConfigured) as context:
            self.validator.validate(VALID_PURCHASE_TOKEN, self.PRODUCT_SKU)

        self.assertIn("Invalid Google Play configuration.", str(context.exception))
