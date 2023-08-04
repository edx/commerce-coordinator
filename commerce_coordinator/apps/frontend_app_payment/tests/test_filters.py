""" frontend_app_payment filter Tests"""

from unittest import TestCase
from unittest.mock import patch

from django.test import override_settings
from edx_django_utils.cache import TieredCache

from commerce_coordinator.apps.core.cache import CachePaymentStates, get_payment_state_cache_key
from commerce_coordinator.apps.core.constants import PaymentState
from commerce_coordinator.apps.frontend_app_payment.filters import DraftPaymentRequested, PaymentProcessingRequested
from commerce_coordinator.apps.titan.tests.test_clients import ORDER_UUID


class TestDraftPaymentRequestedFilter(TestCase):
    """ A pytest Test Case for then `DraftPaymentRequested` """

    @override_settings(
        OPEN_EDX_FILTERS_CONFIG={
            "org.edx.coordinator.frontend_app_payment.payment.draft.requested.v1": {
                "fail_silently": False,
                "pipeline": [
                    'commerce_coordinator.apps.titan.pipeline.GetTitanActiveOrder',
                ]
            },
        },
    )
    @patch('commerce_coordinator.apps.titan.pipeline.GetTitanActiveOrder.run_filter')
    def test_filter_when_payment_exist_in_titan(self, mock_pipeline):
        """
        Test when Payment exists in Titan system.
        """

        mock_payment = {
            'payment_data': {
                'payment_number': '12345',
                'order_uuid': ORDER_UUID,
                'key_id': 'test-code',
                'state': PaymentState.PROCESSING.value
            },
        }
        mock_pipeline.return_value = mock_payment
        filter_params = {
            'edx_lms_user_id': 1,
        }
        payment_details = DraftPaymentRequested.run_filter(**filter_params)
        self.assertEqual(mock_payment.get('payment_data'), payment_details['capture_context'])


class TestPaymentProcessingRequestedFilter(TestCase):
    """ A pytest Test Case for then `PaymentProcessingRequested` """

    @override_settings(
        OPEN_EDX_FILTERS_CONFIG={
            "org.edx.coordinator.frontend_app_payment.payment.processing.requested.v1": {
                "fail_silently": False,
                "pipeline": [
                    'commerce_coordinator.apps.titan.pipeline.GetTitanPayment',
                    'commerce_coordinator.apps.titan.pipeline.ValidatePaymentReadyForProcessing',
                    'commerce_coordinator.apps.titan.pipeline.UpdateBillingAddress',
                    'commerce_coordinator.apps.stripe.pipeline.ConfirmPayment',
                    'commerce_coordinator.apps.titan.pipeline.UpdateTitanPayment',
                ]
            },
        },
    )
    @patch('commerce_coordinator.apps.titan.pipeline.GetTitanPayment.run_filter')
    @patch('commerce_coordinator.apps.titan.pipeline.UpdateBillingAddress.run_filter')
    @patch('commerce_coordinator.apps.stripe.pipeline.ConfirmPayment.run_filter')
    @patch('commerce_coordinator.apps.titan.pipeline.UpdateTitanPayment.run_filter')
    def test_filter_when_payment_exist_in_titan(
        self,
        mock_update_titan_payment_step,
        mock_confirm_payment_step,
        mock_update_billing_address_step,
        mock_get_titan_payment_step,
    ):
        """
        Test when Payment exists in Titan system.
        """

        mock_payment = {
            'payment_data': {
                'payment_number': 'test-payment-number',
                'order_uuid': ORDER_UUID,
                'key_id': 'test-intent-id',
                'state': PaymentState.PROCESSING.value
            }
        }
        mock_billing_details_data = {
            'billing_address_data': {
                'address1': 'test address',
                'address2': '1',
                'city': 'a place',
                'company': 'a company',
                'countryIso': 'US',
                'firstName': 'test',
                'lastName': 'mctester',
                'phone': '5558675309',
                'stateName': 'MA',
                'zipcode': '55555',
            }
        }
        mock_get_titan_payment_step.return_value = mock_payment
        mock_update_billing_address_step.return_value = mock_billing_details_data
        mock_confirm_payment_step.return_value = mock_payment
        mock_update_titan_payment_step.return_value = mock_payment

        filter_params = {
            'order_uuid': ORDER_UUID,
            'payment_number': 'test-payment-number',
            'payment_intent_id': 'test-intent-id',
            'skus': ['test-sku'],
        }
        payment_details = PaymentProcessingRequested.run_filter(**filter_params)
        expected_payment = {**mock_payment, **mock_billing_details_data, **filter_params}
        self.assertEqual(expected_payment, payment_details)
        payment_state_processing_cache_key = get_payment_state_cache_key(
            filter_params['payment_number'], CachePaymentStates.PROCESSING.value
        )
        cached_response = TieredCache.get_cached_response(payment_state_processing_cache_key)
        self.assertTrue(cached_response.is_found)

    @override_settings(
        OPEN_EDX_FILTERS_CONFIG={
            "org.edx.coordinator.frontend_app_payment.payment.processing.requested.v1": {
                "fail_silently": False,
                "pipeline": [
                    'commerce_coordinator.apps.titan.pipeline.UpdateTitanPayment',
                ]
            },
        },
    )
    @patch('commerce_coordinator.apps.titan.pipeline.UpdateTitanPayment.run_filter')
    def test_pipeline_no_result(self, mock_pipeline):
        """
        Test pipeline does not return payment
        """
        TieredCache.dangerous_clear_all_tiers()
        payment_number = '1234'
        mock_pipeline.return_value = {}
        filter_params = {
            'number': payment_number,
            'responseCode': 'a_stripe_response_code',
            'state': PaymentState.PROCESSING.value,
        }
        payment_details = PaymentProcessingRequested.run_filter(**filter_params)
        self.assertEqual(filter_params, payment_details)
