""" Titan Pipeline Tests"""
from unittest import TestCase
from unittest.mock import patch

from stripe.error import StripeError

from commerce_coordinator.apps.core.constants import PaymentState
from commerce_coordinator.apps.stripe.exceptions import StripeIntentCreateAPIError, StripeIntentUpdateAPIError
from commerce_coordinator.apps.stripe.pipeline import CreateOrGetStripeDraftPayment, UpdateStripeDraftPayment
from commerce_coordinator.apps.titan.tests.test_clients import ORDER_UUID


class TestCreateOrGetStripeDraftPaymentStep(TestCase):
    """A pytest Test case for the CreateOrGetStripeDraftPayment Pipeline Step"""
    @patch('commerce_coordinator.apps.titan.clients.TitanAPIClient.create_payment')
    @patch('commerce_coordinator.apps.stripe.clients.StripeAPIClient.create_payment_intent')
    def test_pipeline_step(self, mock_create_payment_intent, mock_create_payment):
        create_draft_payment_pipe = CreateOrGetStripeDraftPayment("test_pipe", None)
        mock_active_order = {
            'basket_id': ORDER_UUID,
            'item_total': '100.0',
        }
        intent_id = 'ch_3MebJMAa00oRYTAV1C26pHmmj572'
        client_sec_id = 'pi_hiya_secret_howsitgoing'
        mock_create_payment_intent.return_value = {
            'id': intent_id,
            'client_secret': client_sec_id
        }
        recent_payment = {
            'amount': '228.0',
            'payment_number': 'PDHB22WS',
            'order_uuid': ORDER_UUID,
            'key_id': client_sec_id,
            'state': PaymentState.CHECKOUT.value,
        }
        mock_create_payment.return_value = {
            'amount': recent_payment['amount'],
            'number': recent_payment['payment_number'],
            'orderUuid': recent_payment['order_uuid'],
            'responseCode': recent_payment['key_id'],
            'state': recent_payment['state'],
        }

        # Test when existing payment exists.
        result: dict = create_draft_payment_pipe.run_filter(mock_active_order, recent_payment, edx_lms_user_id=12)
        mock_create_payment_intent.assert_not_called()
        mock_create_payment.assert_not_called()
        self.assertEqual(recent_payment['key_id'], result['payment_data']['key_id'])

        # Test when existing payment is in FAILED state.
        recent_payment['state'] = PaymentState.FAILED.value
        result: dict = create_draft_payment_pipe.run_filter(mock_active_order, recent_payment, edx_lms_user_id=12)
        mock_create_payment_intent.assert_called()
        mock_create_payment.assert_called()
        self.assertEqual(recent_payment['key_id'], result['payment_data']['key_id'])

        # Test when existing payment does not exist.
        result: dict = create_draft_payment_pipe.run_filter(mock_active_order, recent_payment=None, edx_lms_user_id=12)
        mock_create_payment_intent.assert_called()
        mock_create_payment.assert_called()
        self.assertEqual(recent_payment['key_id'], result['payment_data']['key_id'])

        # Test Error while creating payment intent
        mock_create_payment_intent.side_effect = StripeError
        with self.assertRaises(StripeIntentCreateAPIError):
            create_draft_payment_pipe.run_filter(mock_active_order, recent_payment=None)


class TestUpdateStripeDraftPaymentStep(TestCase):
    """A pytest Test case for the CreateOrGetStripeDraftPayment Pipeline Step"""
    @patch('commerce_coordinator.apps.stripe.clients.StripeAPIClient.update_payment_intent')
    def test_pipeline_step(self, mock_update_payment_intent):
        create_update_payment_pipe = UpdateStripeDraftPayment("test_pipe", None)
        mock_order_data = {
            'basket_id': ORDER_UUID,
            'item_total': '100.0',
        }
        intent_id = 'ch_3MebJMAa00oRYTAV1C26pHmmj572'
        mock_update_payment_intent.return_value = {
            'id': intent_id,
        }
        mock_payment_data = {
            'amount': '228.0',
            'payment_number': 'PDHB22WS',
            'order_uuid': ORDER_UUID,
            'key_id': intent_id,
            'state': PaymentState.CHECKOUT.value,
            'payment_intent_id': 'pi_somecode'
        }

        result: dict = create_update_payment_pipe.run_filter(mock_order_data, mock_payment_data)
        mock_update_payment_intent.assert_called()
        self.assertEqual(mock_payment_data['key_id'], result['payment_data']['key_id'])

        # Test Error while updating payment intent
        mock_update_payment_intent.side_effect = StripeError
        with self.assertRaises(StripeIntentUpdateAPIError):
            create_update_payment_pipe.run_filter(mock_order_data, mock_payment_data)
