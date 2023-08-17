""" Stripe Pipeline Tests"""
from unittest import TestCase
from unittest.mock import patch

from stripe.error import StripeError

from commerce_coordinator.apps.core.constants import OrderPaymentState, PaymentState
from commerce_coordinator.apps.stripe.constants import Currency
from commerce_coordinator.apps.stripe.exceptions import (
    StripeIntentConfirmAPIError,
    StripeIntentCreateAPIError,
    StripeIntentRetrieveAPIError,
    StripeIntentUpdateAPIError
)
from commerce_coordinator.apps.stripe.pipeline import (
    ConfirmPayment,
    CreateOrGetStripeDraftPayment,
    GetStripeDraftPayment,
    UpdateStripeDraftPayment,
    UpdateStripePayment
)
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
            'payment_state': OrderPaymentState.BALANCE_DUE.value
        }
        intent_id = 'ch_3MebJMAa00oRYTAV1C26pHmmj572'
        client_sec_id = 'pi_hiya_secret_howsitgoing'
        mock_create_payment_intent.return_value = {
            'id': intent_id,
            'client_secret': client_sec_id
        }
        mock_payment_data = {
            'amount': '228.0',
            'payment_number': 'PDHB22WS',
            'order_uuid': ORDER_UUID,
            'key_id': client_sec_id,
            'state': PaymentState.CHECKOUT.value,
        }
        mock_create_payment.return_value = {
            'amount': mock_payment_data['amount'],
            'number': mock_payment_data['payment_number'],
            'orderUuid': mock_payment_data['order_uuid'],
            'responseCode': mock_payment_data['key_id'],
            'state': mock_payment_data['state'],
        }

        # Test with payment_data.
        result: dict = create_draft_payment_pipe.run_filter(
            order_data=mock_active_order,
            payment_data=mock_payment_data,
            edx_lms_user_id=12,
        )
        mock_create_payment_intent.assert_not_called()
        mock_create_payment.assert_not_called()
        self.assertIsNone(result)

        # Test without payment_data.
        mock_create_payment_intent.reset_mock()
        mock_create_payment.reset_mock()
        result: dict = create_draft_payment_pipe.run_filter(
            order_data=mock_active_order,
            edx_lms_user_id=12,
        )
        mock_create_payment_intent.assert_called()
        mock_create_payment.assert_called()
        self.assertEqual(mock_payment_data['key_id'], result['payment_data']['key_id'])

        # Test Error while creating payment intent
        mock_create_payment_intent.side_effect = StripeError
        with self.assertRaises(StripeIntentCreateAPIError):
            create_draft_payment_pipe.run_filter(mock_active_order, mock_payment_data=None, edx_lms_user_id=12)


class TestGetStripeDraftPaymentStep(TestCase):
    """A pytest Test case for the GetStripeDraftPayment Pipeline Step"""
    @patch('commerce_coordinator.apps.stripe.clients.StripeAPIClient.retrieve_payment_intent')
    def test_pipeline_step(self, mock_retrieve_payment_intent):
        get_draft_payment_pipe = GetStripeDraftPayment("test_pipe", None)
        intent_id = 'pi_3MebJMAa00oRYTAV1C26pHmmj572'
        mock_payment_data = {
            'key_id': intent_id
        }
        client_sec_id = 'pi_3MebJMAa00oRYTAV1C26pHmmj572_secret_I1qcyrP4t9pxg5DuEDu4Cy4MS'
        mock_payment_intent_data = {
            'id': intent_id,
            'client_secret': client_sec_id
        }
        mock_retrieve_payment_intent.return_value = mock_payment_intent_data

        # Test when payment_intent_data does not exist.
        result: dict = get_draft_payment_pipe.run_filter(payment_data=mock_payment_data)
        mock_retrieve_payment_intent.assert_called_with(intent_id)
        self.assertEqual(intent_id, result['payment_intent_data']['id'])
        self.assertEqual(client_sec_id, result['payment_data']['key_id'])

        # Test when payment_intent_data already exists.
        mock_retrieve_payment_intent.reset_mock()
        result: dict = get_draft_payment_pipe.run_filter(
            payment_data=mock_payment_data,
            payment_intent_data=mock_payment_intent_data,
        )
        mock_retrieve_payment_intent.assert_not_called()
        self.assertDictEqual({}, result)

        # Test when Stripe API gives error.
        mock_retrieve_payment_intent.side_effect = StripeError
        with self.assertRaises(StripeIntentRetrieveAPIError):
            get_draft_payment_pipe.run_filter(payment_data=mock_payment_data)


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
            'amount': '100.0',
            'payment_number': 'PDHB22WS',
            'order_uuid': ORDER_UUID,
            'key_id': intent_id,
            'state': PaymentState.CHECKOUT.value,
            'payment_intent_id': 'pi_somecode'
        }

        result: dict = create_update_payment_pipe.run_filter(
            edx_lms_user_id=1,
            order_data=mock_order_data,
            payment_data=mock_payment_data,
        )
        mock_update_payment_intent.assert_called_with(
            edx_lms_user_id=1,
            payment_intent_id=intent_id,
            order_uuid=ORDER_UUID,
            current_payment_number='PDHB22WS',
            amount_in_cents=10000,
            currency='usd',
        )
        self.assertEqual(intent_id, result['payment_intent_data']['id'])

        # Test Error while updating payment intent
        mock_update_payment_intent.side_effect = StripeError
        with self.assertRaises(StripeIntentUpdateAPIError):
            create_update_payment_pipe.run_filter(
                edx_lms_user_id=1,
                order_data=mock_order_data,
                payment_data=mock_payment_data,
            )


class TestUpdateStripePaymentStep(TestCase):
    """A pytest Test case for the UpdateStripePayment Pipeline Step"""
    @patch('commerce_coordinator.apps.stripe.clients.StripeAPIClient.update_payment_intent')
    def test_pipeline_step(self, mock_update_payment_intent):
        update_payment_pipe = UpdateStripePayment("test_pipe", None)
        intent_id = 'ch_3MebJMAa00oRYTAV1C26pHmmj572'
        mock_update_payment_intent.return_value = {
            'id': intent_id,
        }
        mock_payment_data = {
            'edx_lms_user_id': 1,
            'payment_intent_id': intent_id,
            'order_uuid': ORDER_UUID,
            'amount_in_cents': '228.0',
            'currency': Currency.USD.value,
            'payment_number': 'PDHB22WS',
        }

        result: dict = update_payment_pipe.run_filter(**mock_payment_data)
        mock_update_payment_intent.assert_called()
        self.assertEqual(mock_payment_data['payment_intent_id'], result['provider_response_body']['id'])

        # Test Error while updating payment intent
        mock_update_payment_intent.side_effect = StripeError
        with self.assertRaises(StripeIntentUpdateAPIError):
            update_payment_pipe.run_filter(**mock_payment_data)


class TestConfirmPaymentStep(TestCase):
    """A pytest Test case for the ConfirmPayment Pipeline Step"""
    @patch('commerce_coordinator.apps.stripe.clients.StripeAPIClient.confirm_payment_intent')
    def test_pipeline_step(self, mock_confirm_payment_intent):
        confirm_payment_pipe = ConfirmPayment("test_pipe", None)
        intent_id = 'ch_3MebJMAa00oRYTAV1C26pHmmj572'
        mock_confirm_payment_intent.return_value = {
            'id': intent_id,
        }
        mock_payment_data = {
            'amount': '228.0',
            'payment_number': 'PDHB22WS',
            'order_uuid': ORDER_UUID,
            'key_id': intent_id,
            'state': PaymentState.CHECKOUT.value,
        }

        result: dict = confirm_payment_pipe.run_filter(payment_data=mock_payment_data)
        mock_confirm_payment_intent.assert_called_with(payment_intent_id=intent_id)
        self.assertEqual(intent_id, result['payment_intent_data']['id'])

        # Test Error while updating payment intent
        mock_confirm_payment_intent.side_effect = StripeError
        with self.assertRaises(StripeIntentConfirmAPIError):
            confirm_payment_pipe.run_filter(payment_data=mock_payment_data)
