"""
Test suite for IAPPaymentProcessor.
This module contains unit tests for the IAPPaymentProcessor class, which handles
In-App Purchase (IAP) validation for Android (Google Play) and iOS (App Store) platforms.
"""

# pylint: disable=protected-access

import unittest
from unittest.mock import MagicMock, patch

from commerce_coordinator.apps.iap.payment_processor import IAPPaymentProcessor, RedundantPaymentError


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
        self.MockCTClient.return_value.get_payment_by_transaction_id.return_value = None

        request_data = {
            'purchase_token': 'test_token',
            'course_run_key': 'test_course',
            'payment_processor': 'android-iap',
        }
        result = self.processor.validate_iap(request_data, cart='cart_123')

        self.assertEqual(result['transaction_id'], 'transaction_123')

    @patch('commerce_coordinator.apps.iap.payment_processor.GooglePlayValidator')
    def test_android_validation_failure(self, MockGooglePlayValidator):
        MockGooglePlayValidator.return_value.validate.return_value = {'error': 'Invalid purchase'}

        request_data = {
            'purchase_token': 'test_token',
            'payment_processor': 'android-iap',
        }
        result = self.processor.validate_iap(request_data, cart='cart_123')

        self.assertIn('error', result)

    @patch('commerce_coordinator.apps.iap.payment_processor.logger')
    def test_android_validation_errors(self, mock_logger):
        test_cases = [
            ({'raw_response': {}}, "Android IAP validation missing transaction ID."),
            ({'raw_response': {'orderId': 'txn_123'}, 'is_canceled': True},
             "Android payment is cancelled for [txn_123]"),
            ({'raw_response': {'orderId': 'txn_123'}, 'is_expired': True}, "Android payment is expired for [txn_123]")
        ]

        for input_data, expected_log in test_cases:
            with self.subTest(input_data=input_data):
                result = self.processor._handle_android_validation(input_data, cart='cart_123')
                self.assertIn('error', result)
                self.assertEqual(result['error'], expected_log)
                mock_logger.error.assert_called_with(expected_log)

    @patch('commerce_coordinator.apps.iap.payment_processor.GooglePlayValidator')
    def test_android_redundant_payment_error(self, MockGooglePlayValidator):
        MockGooglePlayValidator.return_value.validate.return_value = {
            'raw_response': {'orderId': 'txn_123'}
        }
        self.MockCTClient.return_value.get_payment_by_transaction_id.return_value = True

        with self.assertRaises(RedundantPaymentError) as context:
            self.processor.validate_iap({'payment_processor': 'android-iap'}, cart='cart_123')

        self.assertIn("Execute payment failed for basket [cart_123]. Redundant payment.", str(context.exception))

    def test_ios_validation_errors(self):
        test_cases = [
            ({'receipt': {'in_app': []}}, {'error': 'No matching purchase found'}),
            ({'receipt': {'in_app': [{'product_id': 'wrong_sku', 'original_transaction_id': 'txn_999'}]}},
             {'error': 'No matching purchase found'}),
            ({
                 'receipt': {
                     'in_app': [
                         {
                             'product_id': 'test_sku',
                             'original_transaction_id': 'txn_123',
                             'cancellation_reason': 'user'
                         }
                     ]
                 }
             },
             {'error': 'iOS payment is cancelled for [txn_123] in basket [123]'}),
            ({'receipt': {}}, {'error': 'No matching purchase found'}),
        ]

        for input_data, expected_output in test_cases:
            with self.subTest(input_data=input_data):
                mock_basket = MagicMock()
                mock_basket.id = 123
                self.processor.client.get_payment_by_transaction_id.return_value = None
                result = self.processor._handle_ios_validation(input_data, 'test_sku', mock_basket.id)
                self.assertEqual(result, expected_output)

    def test_ios_redundant_payment_error(self):
        self.MockCTClient.return_value.get_payment_by_transaction_id.return_value = True

        with self.assertRaises(RedundantPaymentError) as context:
            self.processor._handle_ios_validation(
                {'receipt': {'in_app': [{'product_id': 'test_sku', 'original_transaction_id': 'txn_123'}]}},
                'test_sku', 'cart_123'
            )

        self.assertIn("Execute payment failed for basket [cart_123]. Redundant payment.", str(context.exception))

    def test_missing_payment_processor(self):
        request_data = {
            'purchase_token': 'token123',
            'course_run_key': 'sku123'
        }
        result = self.processor.validate_iap(request_data, cart='cart_123')
        self.assertIn('error', result)
        self.assertEqual(result['error'], "Missing 'payment_processor' in request data.")

    def test_unsupported_payment_processor(self):
        request_data = {
            'purchase_token': 'token123',
            'payment_processor': 'unsupported_processor'
        }
        result = self.processor.validate_iap(request_data, cart='cart_123')
        self.assertIn('error', result)
        self.assertIn('Unsupported payment_processor', result['error'])

    @patch('commerce_coordinator.apps.iap.payment_processor.IOSValidator')
    def test_ios_validation_success(self, MockIOSValidator):
        MockIOSValidator.return_value.validate.return_value = {
            'receipt': {'in_app': [{'product_id': 'test_sku', 'original_transaction_id': 'transaction_456'}]}
        }
        self.MockCTClient.return_value.get_payment_by_transaction_id.return_value = None

        request_data = {
            'purchase_token': 'test_token',
            'course_run_key': 'test_sku',
            'payment_processor': 'ios-iap',
        }
        result = self.processor.validate_iap(request_data, cart='cart_123')

        self.assertEqual(result['transaction_id'], 'transaction_456')
