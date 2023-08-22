""" frontend_app_payment filter Tests"""

from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

import ddt
from django.test import override_settings
from edx_django_utils.cache import TieredCache

from commerce_coordinator.apps.core.cache import CachePaymentStates, get_payment_state_cache_key
from commerce_coordinator.apps.core.constants import OrderPaymentState, PaymentState
from commerce_coordinator.apps.frontend_app_payment.filters import (
    DraftPaymentRequested,
    PaymentProcessingRequested,
    PaymentRequested
)
from commerce_coordinator.apps.titan.tests.test_clients import ORDER_UUID


class TestDraftPaymentRequestedFilter(TestCase):
    """ A pytest Test Case for then `DraftPaymentRequested` """

    @override_settings(
        OPEN_EDX_FILTERS_CONFIG={
            "org.edx.coordinator.frontend_app_payment.payment.draft.requested.v1": {
                "fail_silently": False,
                "pipeline": [
                    'commerce_coordinator.apps.titan.pipeline.GetTitanActiveOrder',
                    'commerce_coordinator.apps.titan.pipeline.ValidateOrderReadyForDraftPayment',
                    'commerce_coordinator.apps.stripe.pipeline.GetStripeDraftPayment',
                    'commerce_coordinator.apps.stripe.pipeline.CreateOrGetStripeDraftPayment',
                    'commerce_coordinator.apps.stripe.pipeline.UpdateStripeDraftPayment',
                ]
            },
        },
    )
    @patch('commerce_coordinator.apps.titan.pipeline.GetTitanActiveOrder.run_filter')
    @patch('commerce_coordinator.apps.titan.pipeline.ValidateOrderReadyForDraftPayment.run_filter')
    @patch('commerce_coordinator.apps.stripe.pipeline.GetStripeDraftPayment.run_filter')
    @patch('commerce_coordinator.apps.stripe.pipeline.CreateOrGetStripeDraftPayment.run_filter')
    @patch('commerce_coordinator.apps.stripe.pipeline.UpdateStripeDraftPayment.run_filter')
    def test_filter_when_payment_exist_in_titan(
        self,
        mock_update_draft_payment_step,
        mock_create_draft_payment_step,
        mock_get_draft_payment_step,
        mock_validate_draft_ready_step,
        mock_get_active_order_step,
    ):
        """
        Test when Payment exists in Titan system.
        """

        mock_payment_intent_id = 'pi_123456789012345'

        # Start with final output from UpdateDraftPayment, then morph each
        # pipeline output mock:
        mock_update_draft_payment_output = {
            'order_data': {
                'basket_id': ORDER_UUID,
                'item_total': '100.0',
                'payment_state': OrderPaymentState.BALANCE_DUE.value,
            },
            'payment_data': {
                'key_id': mock_payment_intent_id,
                'order_uuid': ORDER_UUID,
                'payment_number': '12345',
                'state': PaymentState.CHECKOUT.value,
            },
            'payment_intent_data': {
                'id': mock_payment_intent_id,
                'client_secret': mock_payment_intent_id + 'secret_12345',
            }
        }
        mock_update_draft_payment_step.return_value = mock_update_draft_payment_output

        # CreateOrGetStripeDraftPayment output is the same as UpdateStripeDraftPayment's.
        mock_create_draft_payment_output = deepcopy(mock_update_draft_payment_output)
        mock_create_draft_payment_step.return_value = mock_create_draft_payment_output

        # GetStripeDraftPayment output won't have payment_intent_data.
        mock_get_draft_payment_output = deepcopy(mock_update_draft_payment_output)
        del mock_get_draft_payment_output['payment_intent_data']
        mock_get_draft_payment_step.return_value = mock_get_draft_payment_output

        # ValidateOrderReadyForDraftPayment output won't have payment_data.
        mock_validate_draft_ready_output = deepcopy(mock_get_draft_payment_output)
        del mock_validate_draft_ready_output['payment_data']
        mock_validate_draft_ready_step.return_value = mock_validate_draft_ready_output

        # GetTitanActiveOrder output is the same as ValidateOrderReadyForDraftPayment's.
        mock_get_active_order_output = deepcopy(mock_validate_draft_ready_output)
        mock_get_active_order_step.return_value = mock_get_active_order_output

        # Build expected output:
        expected_output = deepcopy(mock_update_draft_payment_output['payment_data'])
        # order_uuid is renamed to order_id by filter:
        expected_output['order_id'] = expected_output.pop('order_uuid')

        # Run filter:
        filter_params = {
            'edx_lms_user_id': 1,
        }
        output = DraftPaymentRequested.run_filter(**filter_params)

        # Check output matches expected:
        self.assertEqual(expected_output, output['capture_context'])


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
                'state': PaymentState.CHECKOUT.value
            }
        }
        mock_pending_payment = {
            'payment_data': {
                'payment_number': 'test-payment-number',
                'order_uuid': ORDER_UUID,
                'key_id': 'test-intent-id',
                'state': PaymentState.PENDING.value
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
        mock_confirm_payment_step.return_value = mock_pending_payment
        mock_update_titan_payment_step.return_value = mock_pending_payment

        filter_params = {
            'order_uuid': ORDER_UUID,
            'payment_number': 'test-payment-number',
            'payment_intent_id': 'test-intent-id',
            'skus': ['test-sku'],
        }
        payment_details = PaymentProcessingRequested.run_filter(**filter_params)
        expected_payment = {**mock_pending_payment, **mock_billing_details_data, **filter_params}
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
            'state': PaymentState.PENDING.value,
        }
        payment_details = PaymentProcessingRequested.run_filter(**filter_params)
        self.assertEqual(filter_params, payment_details)


@ddt.ddt
class TestPaymentRequestedFilter(TestCase):
    """ A pytest Test Case for `PaymentRequested` """

    @ddt.data(
        PaymentState.CHECKOUT.value,
        PaymentState.COMPLETED.value,
        PaymentState.FAILED.value,
        PaymentState.PENDING.value,
    )
    @override_settings(
        OPEN_EDX_FILTERS_CONFIG={
            "org.edx.coordinator.frontend_app_payment.payment.get.requested.v1": {
                "fail_silently": False,
                "pipeline": [
                    'commerce_coordinator.apps.titan.pipeline.GetTitanPayment',
                ]
            },
        },
    )
    @patch('commerce_coordinator.apps.titan.pipeline.GetTitanPayment.run_filter')
    def test_filter(self, payment_state, mock_get_payment_step):
        """
        Test when Payment exists in Titan system.
        """
        mock_payment_number = 'test-payment-number'
        mock_get_payment_step_output = {
            'payment_data': {
                'payment_number': mock_payment_number,
                'order_uuid': ORDER_UUID,
                'key_id': 'test-intent-id',
                'state': payment_state
            }
        }
        mock_get_payment_step.return_value = mock_get_payment_step_output

        # Build expected output:
        expected_output = deepcopy(mock_get_payment_step_output['payment_data'])

        # Run filter:
        TieredCache.dangerous_clear_all_tiers()
        filter_params = {
            'payment_number': mock_payment_number,
        }
        output = PaymentRequested.run_filter(filter_params)

        # Check output matches expected:
        self.assertEqual(expected_output, output)
