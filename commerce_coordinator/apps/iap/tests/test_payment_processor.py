"""
Test suite for IAPPaymentProcessor.
This module contains unit tests for the IAPPaymentProcessor class, which handles
In-App Purchase (IAP) validation for Android (Google Play) and iOS (App Store) platforms.
"""

# pylint: disable=protected-access

import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from commerce_coordinator.apps.iap.payment_processor import (
    IAPPaymentProcessor,
    PaymentError,
    RedundantPaymentError,
    UserCancelled,
    ValidationError
)


class TestIAPPaymentProcessor(unittest.TestCase):
    """
    Test suite for IAPPaymentProcessor class.
    """

    def setUp(self):
        patcher = patch('commerce_coordinator.apps.iap.payment_processor.CommercetoolsAPIClient')
        self.MockCTClient = patcher.start()
        self.addCleanup(patcher.stop)
        self.MockCTClient.return_value = MagicMock()
        self.processor = IAPPaymentProcessor()

    @patch('commerce_coordinator.apps.iap.payment_processor.GooglePlayValidator')
    def test_android_validation_success(self, MockGooglePlayValidator):
        MockGooglePlayValidator.return_value.validate.return_value = {
            'is_canceled': False,
            'is_expired': False,
            'raw_response': {'orderId': 'transaction_123'}
        }
        self.MockCTClient.return_value.get_payment_by_transaction_interaction_id.return_value = None

        request_data = {
            'purchase_token': 'test_token',
            'course_run_key': 'test_course',
            'payment_processor': 'android-iap',
        }
        result = self.processor.validate_iap(request_data, cart_id='cart_123', price=100)

        self.assertEqual(result['transaction_id'], 'transaction_123')

    @patch('commerce_coordinator.apps.iap.payment_processor.GooglePlayValidator')
    def test_android_validation_failure_raises_validation_error(self, MockGooglePlayValidator):
        MockGooglePlayValidator.return_value.validate.return_value = {'error': 'Invalid purchase'}

        request_data = {
            'purchase_token': 'test_token',
            'payment_processor': 'android-iap',
        }
        with self.assertRaises(ValidationError) as cm:
            self.processor.validate_iap(request_data, cart_id='cart_123', price=100)
        self.assertIn('Invalid purchase', str(cm.exception))

    def test_android_handle_android_validation_errors(self):
        with self.assertRaises(ValidationError):
            self.processor._handle_android_validation({'raw_response': {}}, cart_id='cart_123')

        with self.assertRaises(UserCancelled):
            self.processor._handle_android_validation({
                'raw_response': {'orderId': 'txn_123'},
                'is_canceled': True
            }, cart_id='cart_123')

        with self.assertRaises(PaymentError):
            self.processor._handle_android_validation({
                'raw_response': {'orderId': 'txn_123'},
                'is_expired': True
            }, cart_id='cart_123')

    @patch('commerce_coordinator.apps.iap.payment_processor.GooglePlayValidator')
    def test_android_redundant_payment_error(self, MockGooglePlayValidator):
        MockGooglePlayValidator.return_value.validate.return_value = {
            'raw_response': {'orderId': 'txn_123'}
        }
        self.MockCTClient.return_value.get_payment_by_transaction_interaction_id.return_value = True

        with self.assertRaises(RedundantPaymentError):
            self.processor.validate_iap(
                {'purchase_token': 'token', 'payment_processor': 'android-iap'},
                cart_id='cart_123',
                price=100
            )

    def test_ios_handle_ios_validation_errors(self):
        with self.assertRaises(ValidationError):
            self.processor._handle_ios_validation({'receipt': {'in_app': []}}, 'test_sku', 'cart_123')

        with self.assertRaises(ValidationError):
            self.processor._handle_ios_validation(
                {'receipt': {'in_app': [{'product_id': 'wrong_sku', 'original_transaction_id': 'txn_999'}]}},
                'test_sku', 'cart_123')

        with self.assertRaises(UserCancelled):
            self.processor._handle_ios_validation(
                {'receipt': {'in_app': [{
                    'product_id': 'test_sku',
                    'original_transaction_id': 'txn_123',
                    'cancellation_reason': 'user'}]}},
                'test_sku', 'cart_123')

    def test_ios_redundant_payment_error(self):
        self.MockCTClient.return_value.get_payment_by_transaction_interaction_id.return_value = True

        with self.assertRaises(RedundantPaymentError):
            self.processor._handle_ios_validation(
                {'receipt': {'in_app': [{
                    'product_id': 'test_sku',
                    'original_transaction_id': 'txn_123'}]}},
                'test_sku', 'cart_123')

    def test_unsupported_payment_processor_raises_validation_error(self):
        request_data = {
            'purchase_token': 'token123',
            'payment_processor': 'unsupported_processor'
        }
        with self.assertRaises(ValidationError):
            self.processor.validate_iap(request_data, cart_id='cart_123', price=100)

    @patch('commerce_coordinator.apps.iap.payment_processor.IOSValidator')
    def test_ios_validation_success(self, MockIOSValidator):
        MockIOSValidator.return_value.validate.return_value = {
            'receipt': {'in_app': [{'product_id': 'test_sku', 'original_transaction_id': 'transaction_456'}]}
        }
        self.MockCTClient.return_value.get_payment_by_transaction_interaction_id.return_value = None

        request_data = {
            'purchase_token': 'test_token',
            'course_run_key': 'test_sku',
            'payment_processor': 'ios-iap',
        }
        result = self.processor.validate_iap(request_data, cart_id='cart_123', price=100)

        self.assertEqual(result['transaction_id'], 'transaction_456')

    @patch('commerce_coordinator.apps.iap.payment_processor.GooglePlayValidator')
    def test_android_created_at_parsing(self, MockGooglePlayValidator):
        MockGooglePlayValidator.return_value.validate.return_value = {
            'is_canceled': False,
            'is_expired': False,
            'raw_response': {
                'orderId': 'transaction_789',
                'purchaseTimeMillis': str(int(datetime(2024, 5, 1, 12, 0, tzinfo=timezone.utc).timestamp() * 1000))
            }
        }
        self.MockCTClient.return_value.get_payment_by_transaction_interaction_id.return_value = None

        request_data = {
            'purchase_token': 'token',
            'course_run_key': 'course',
            'payment_processor': 'android-iap',
        }
        result = self.processor.validate_iap(request_data, cart_id='cart_001', price=100)

        self.assertEqual(result['transaction_id'], 'transaction_789')
        self.assertEqual(result['created_at'], '2024-05-01 12:00:00 UTC')

    @patch('commerce_coordinator.apps.iap.payment_processor.IOSValidator')
    def test_ios_created_at_parsing(self, MockIOSValidator):
        MockIOSValidator.return_value.validate.return_value = {
            'receipt': {
                'in_app': [{'product_id': 'test_sku', 'original_transaction_id': 'txn_101'}],
                'receipt_creation_date': '2024-04-20 10:15:30 Etc/GMT'
            }
        }
        self.MockCTClient.return_value.get_payment_by_transaction_interaction_id.return_value = None

        request_data = {
            'purchase_token': 'test_token',
            'course_run_key': 'test_sku',
            'payment_processor': 'ios-iap',
        }
        result = self.processor.validate_iap(request_data, cart_id='cart_123', price=100)

        self.assertEqual(result['transaction_id'], 'txn_101')
        self.assertEqual(result['created_at'], '2024-04-20 10:15:30 Etc/GMT')
