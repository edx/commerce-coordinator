"""Tests for stripe app clients.py."""

from unittest.mock import MagicMock, patch

import ddt
import stripe
from django.conf import settings
from django.test import override_settings
from rest_framework.exceptions import ValidationError

from commerce_coordinator.apps.core.tests.utils import CoordinatorClientTestCase
from commerce_coordinator.apps.stripe.clients import StripeAPIClient

# Sentinel values.
TEST_ORDER_UUID = 'abcdef01-1234-5678-90ab-cdef01234567'
TEST_PAYMENT_NUMBER = 12345
TEST_PAYMENT_INTENT_ID = 'pi_AbCdEfGhIjKlMnOpQ1234567'
TEST_CURRENCY_SYMBOL = 'mok'

# Build test PAYMENT_PROCESSOR_CONFIG with sentinel value for Stripe's secret_key.
TEST_SECRET = 'TEST_SECRET'
TEST_PAYMENT_PROCESSOR_CONFIG = settings.PAYMENT_PROCESSOR_CONFIG
TEST_PAYMENT_PROCESSOR_CONFIG['edx']['stripe']['secret_key'] = TEST_SECRET


@ddt.ddt
@override_settings(PAYMENT_PROCESSOR_CONFIG=TEST_PAYMENT_PROCESSOR_CONFIG)
class TestStripeAPIClient(CoordinatorClientTestCase):
    """Tests for StripeAPIClient."""

    expected_headers = {
        'Authorization': 'Bearer ' + TEST_SECRET,
        'Stripe-Version': '2022-08-01; server_side_confirmation_beta=v1',
    }

    def setUp(self):
        self.client = StripeAPIClient()

    def test_create_payment_intent_success(self):
        """
        Check successful call of StripeAPIClient.create_payment_intent() using
        order number as idempotency key.
        """
        # Add Idempotency-Key to expected headers:
        expected_idempotency_key = 'order_number_pi_create_v1_' + TEST_ORDER_UUID
        expected_headers_with_idempot_key = self.expected_headers.copy()
        expected_headers_with_idempot_key['Idempotency-Key'] = expected_idempotency_key

        self.assertJSONClientResponse(
            uut=self.client.create_payment_intent,
            input_kwargs={
                'order_uuid': TEST_ORDER_UUID,
                'amount_in_cents': 10000,
                'currency': 'USD',
            },
            expected_request={
                'amount': ['10000'],
                'currency': ['USD'],
                'description': [TEST_ORDER_UUID],
                'metadata[order_number]': [TEST_ORDER_UUID],
                'metadata[source_system]': ['edx/commerce_coordinator?v=1'],
                'secret_key_confirmation': ['required'],
            },
            request_type='query_string',
            expected_headers=expected_headers_with_idempot_key,
            mock_url='https://api.stripe.com/v1/payment_intents',
            mock_response={
                'id': 'mock_id',
                'mock_stripe_response': 'mock_value'
            },
            expected_output={
                'id': 'mock_id',
                'mock_stripe_response': 'mock_value'
            },
        )

    def test_create_payment_intent_idempotency_error(self):
        """
        Check StripeAPIClient.create_payment_intent() throws
        stripe.error.IdempotencyError when it returns a response indicating the
        previous request used different arguments.
        """
        # Add Idempotency-Key to expected headers:
        expected_idempotency_key = 'order_number_pi_create_v1_' + TEST_ORDER_UUID
        expected_headers_with_idempot_key = self.expected_headers.copy()
        expected_headers_with_idempot_key['Idempotency-Key'] = expected_idempotency_key

        with self.assertRaises(stripe.error.IdempotencyError):
            self.assertJSONClientResponse(
                uut=self.client.create_payment_intent,
                input_kwargs={
                    'order_uuid': TEST_ORDER_UUID,
                    'amount_in_cents': 10000,
                    'currency': 'USD',
                },
                expected_request={
                    'amount': ['10000'],
                    'currency': ['USD'],
                    'description': [TEST_ORDER_UUID],
                    'metadata[order_number]': [TEST_ORDER_UUID],
                    'metadata[source_system]': ['edx/commerce_coordinator?v=1'],
                    'secret_key_confirmation': ['required'],
                },
                request_type='query_string',
                expected_headers=expected_headers_with_idempot_key,
                mock_url='https://api.stripe.com/v1/payment_intents',
                mock_status=400,
                mock_response={
                    'error': {
                        'message':
                            'Keys for idempotent requests can only be used with'
                            'the same parameters they were first used with...',
                        'type':
                            'idempotency_error',
                    },
                },
            )

    def test_create_payment_intent_idempotency_key_in_use(self):
        """
        Check StripeAPIClient.create_payment_intent() throws
        stripe.error.APIError when it returns a response indicating
        there is another request in-flight with the same idempotency key.
        """
        # Add Idempotency-Key to expected headers:
        expected_idempotency_key = 'order_number_pi_create_v1_' + TEST_ORDER_UUID
        expected_headers_with_idempot_key = self.expected_headers.copy()
        expected_headers_with_idempot_key['Idempotency-Key'] = expected_idempotency_key

        with self.assertRaises(stripe.error.APIError):
            self.assertJSONClientResponse(
                uut=self.client.create_payment_intent,
                input_kwargs={
                    'order_uuid': TEST_ORDER_UUID,
                    'amount_in_cents': 10000,
                    'currency': 'USD',
                },
                expected_request={
                    'amount': ['10000'],
                    'currency': ['USD'],
                    'description': [TEST_ORDER_UUID],
                    'metadata[order_number]': [TEST_ORDER_UUID],
                    'metadata[source_system]': ['edx/commerce_coordinator?v=1'],
                    'secret_key_confirmation': ['required'],
                },
                request_type='query_string',
                expected_headers=expected_headers_with_idempot_key,
                mock_url='https://api.stripe.com/v1/payment_intents',
                mock_status=409,
                mock_response={
                    "error": {
                        "code": "idempotency_key_in_use",
                        "doc_url": "https://stripe.com/docs/error-codes/idempotency-key-in-use",
                        "message": "There is currently another in-progress...",
                        "type": "invalid_request_error"
                    },
                },
            )

    @patch("commerce_coordinator.apps.stripe.clients.stripe.PaymentIntent.create")
    @ddt.data(
        (
            {
                "order_uuid": TEST_ORDER_UUID,
                "amount_in_cents": 1,
                "currency": TEST_CURRENCY_SYMBOL
            },
            None
        ),
        (
            {
                "order_uuid": TEST_ORDER_UUID,
                "amount_in_cents": 0,
                "currency": TEST_CURRENCY_SYMBOL
            },
            "Ensure this value is greater than or equal to 1."
        ),
        (
            {
                "order_uuid": None,
                "amount_in_cents": 1,
                "currency": TEST_CURRENCY_SYMBOL
            },
            "This field may not be null."
        ),
        (
            {
                "order_uuid": TEST_ORDER_UUID,
                "amount_in_cents": None,
                "currency": TEST_CURRENCY_SYMBOL
            },
            "This field may not be null."
        ),
        (
            {
                "order_uuid": TEST_ORDER_UUID,
                "amount_in_cents": 1,
                "currency": None
            },
            "This field may not be null."
        ),
        (
            {
                "order_uuid": TEST_ORDER_UUID,
                "amount_in_cents": -1,
                "currency": TEST_CURRENCY_SYMBOL
            },
            "Ensure this value is greater than or equal to 1."
        ),
    )
    @ddt.unpack
    def test_create_payment_intent_arguments(
        self,
        input_args,
        value_error_expected_regex,
        mock_stripe,
    ):
        """
        Check ValidationError is appropriately raised when
        StripeAPIClient.create_payment_intent() is called with bad arguments.
        """
        mock_stripe.return_value = MagicMock()

        if value_error_expected_regex:
            with self.assertRaisesRegex(ValidationError, value_error_expected_regex):
                self.client.create_payment_intent(**input_args)
        else:
            self.assertEqual(
                self.client.create_payment_intent(**input_args),
                mock_stripe.return_value
            )

    def test_retrieve_payment_intent_success(self):
        """
        Check successful call of StripeAPIClient.retrieve_payment_intent().
        """
        self.assertJSONClientResponse(
            uut=self.client.retrieve_payment_intent,
            input_kwargs={
                'payment_intent_id': TEST_PAYMENT_INTENT_ID,
            },
            request_type='query_string',
            expected_headers=self.expected_headers,
            mock_method='GET',
            mock_url=f'https://api.stripe.com/v1/payment_intents/{TEST_PAYMENT_INTENT_ID}',
            mock_response={
                'id': 'mock_id',
                'mock_stripe_response': 'mock_value'
            },
            expected_output={
                'id': 'mock_id',
                'mock_stripe_response': 'mock_value'
            },
        )

    def test_retrieve_payment_intent_failure(self):
        """
        Check failed call of StripeAPIClient.retrieve_payment_intent() throws an error.
        """
        with self.assertRaises(stripe.error.InvalidRequestError):
            self.assertJSONClientResponse(
                uut=self.client.retrieve_payment_intent,
                input_kwargs={
                    'payment_intent_id': TEST_PAYMENT_INTENT_ID,
                },
                request_type='query_string',
                expected_headers=self.expected_headers,
                mock_method='GET',
                mock_url=f'https://api.stripe.com/v1/payment_intents/{TEST_PAYMENT_INTENT_ID}',
                mock_response={
                    "error": {
                        "code": "resource_missing",
                        "doc_url": "https://stripe.com/docs/error-codes/resource-missing",
                        "message": f"No such payment_intent: '{TEST_PAYMENT_INTENT_ID}'",
                        "param": "intent",
                        "type": "invalid_request_error",
                    },
                },
                mock_status=404,
            )

    def test_update_payment_intent_success(self):
        """
        Check successful call of StripeAPIClient.update_payment_intent().
        """
        self.assertJSONClientResponse(
            uut=self.client.update_payment_intent,
            input_kwargs={
                'payment_intent_id': TEST_PAYMENT_INTENT_ID,
                'order_uuid': TEST_ORDER_UUID,
                'current_payment_number': TEST_PAYMENT_NUMBER,
                'amount_in_cents': 10000,
                'currency': 'USD',
            },
            expected_request={
                'amount': ['10000'],
                'currency': ['USD'],
                'description': [TEST_ORDER_UUID],
                'metadata[order_number]': [TEST_ORDER_UUID],
                'metadata[payment_number]': [str(TEST_PAYMENT_NUMBER)],
                'metadata[source_system]': ['edx/commerce_coordinator?v=1'],
            },
            request_type='query_string',
            expected_headers=self.expected_headers,
            mock_url=f'https://api.stripe.com/v1/payment_intents/{TEST_PAYMENT_INTENT_ID}',
            mock_response={
                'id': 'mock_id',
                'mock_stripe_response': 'mock_value'
            },
            expected_output={
                'id': 'mock_id',
                'mock_stripe_response': 'mock_value'
            },
        )

    def test_update_payment_intent_idempotency_error(self):
        """
        Check StripeAPIClient.update_payment_intent() throws
        stripe.error.InvalidRequestError when it returns a response indicating
        the update is on an already confirmed payment.
        """
        with self.assertRaises(stripe.error.InvalidRequestError):
            self.assertJSONClientResponse(
                uut=self.client.update_payment_intent,
                input_kwargs={
                    'payment_intent_id': TEST_PAYMENT_INTENT_ID,
                    'order_uuid': TEST_ORDER_UUID,
                    'current_payment_number': TEST_PAYMENT_NUMBER,
                    'amount_in_cents': 10000,
                    'currency': 'USD',
                },
                expected_request={
                    'amount': ['10000'],
                    'currency': ['USD'],
                    'description': [TEST_ORDER_UUID],
                    'metadata[order_number]': [TEST_ORDER_UUID],
                    'metadata[payment_number]': [str(TEST_PAYMENT_NUMBER)],
                    'metadata[source_system]': ['edx/commerce_coordinator?v=1'],
                },
                request_type='query_string',
                expected_headers=self.expected_headers,
                mock_url=f'https://api.stripe.com/v1/payment_intents/{TEST_PAYMENT_INTENT_ID}',
                mock_status=400,
                mock_response={
                    'error': {
                        'code': 'payment_intent_unexpected_state',
                        'doc_url': 'https://stripe.com/docs/error-codes/payment-intent-unexpected-state',
                        'message':
                            'This PaymentIntent''s amount could not be '
                            'updated because it has a status of succeeded. You '
                            'may only update the amount of a PaymentIntent...',
                        'param': 'amount',
                    },
                },
            )

    def test_confirm_payment_intent_success(self):
        """
        Check successful call of StripeAPIClient.confirm_payment_intent().
        """
        self.assertJSONClientResponse(
            uut=self.client.confirm_payment_intent,
            input_kwargs={
                'payment_intent_id': TEST_PAYMENT_INTENT_ID,
            },
            expected_request={
                'error_on_requires_action': ['True'],
                'expand[0]': ['payment_method'],
            },
            request_type='query_string',
            expected_headers=self.expected_headers,
            mock_url=f'https://api.stripe.com/v1/payment_intents/{TEST_PAYMENT_INTENT_ID}/confirm',
            mock_response={
                'id': 'mock_id',
                'mock_stripe_response': 'mock_value'
            },
            expected_output={
                'id': 'mock_id',
                'mock_stripe_response': 'mock_value'
            },
        )

    def test_confirm_payment_intent_idempotency_error(self):
        """
        Check StripeAPIClient.confirm_payment_intent() throws
        stripe.error.InvalidRequestError when it returns a response indicating
        the confirmation is on an already confirmed payment.
        """
        with self.assertRaises(stripe.error.InvalidRequestError):
            self.assertJSONClientResponse(
                uut=self.client.confirm_payment_intent,
                input_kwargs={
                    'payment_intent_id': TEST_PAYMENT_INTENT_ID,
                },
                expected_request={
                    'error_on_requires_action': ['True'],
                    'expand[0]': ['payment_method'],
                },
                request_type='query_string',
                expected_headers=self.expected_headers,
                mock_url=f'https://api.stripe.com/v1/payment_intents/{TEST_PAYMENT_INTENT_ID}/confirm',
                mock_status=400,
                mock_response={
                    'error': {
                        'code': 'payment_intent_unexpected_state',
                    },
                },
            )
