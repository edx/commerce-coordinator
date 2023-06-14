"""Tests for stripe app clients.py."""

from commerce_coordinator.apps.core.tests.utils import CoordinatorClientTestCase
from commerce_coordinator.apps.stripe.clients import StripeAPIClient

TEST_ORDER_UUID = 'abcdef01-1234-5678-90ab-cdef01234567'


class TestStripeAPIClient(CoordinatorClientTestCase):
    """Tests for StripeAPIClient."""

    expected_headers = {
        'Authorization': 'Bearer SET-ME-PLEASE',
        'Stripe-Version': '2022-08-01; server_side_confirmation_beta=v1',
    }

    def setUp(self):
        self.client = StripeAPIClient()

    def test_create_payment_intent_success(self):
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
                'mock_stripe_response': 'mock_value'
            },
            expected_output={
                'mock_stripe_response': 'mock_value'
            },
        )
