""" PayPal Pipeline Tests"""
from unittest import TestCase
from unittest.mock import patch

from django.conf import settings
from django.test import override_settings
from requests import RequestException

from commerce_coordinator.apps.commercetools.catalog_info.constants import EDX_PAYPAL_PAYMENT_INTERFACE_NAME
from commerce_coordinator.apps.core.constants import PipelineCommand
from commerce_coordinator.apps.paypal.pipeline import GetPayPalPaymentReceipt, RefundPayPalPayment

TEST_PAYMENT_PROCESSOR_CONFIG = settings.PAYMENT_PROCESSOR_CONFIG
ACTIVITY_URL = "https://test.paypal.com/myaccount/activities/"
TEST_PAYMENT_PROCESSOR_CONFIG['edx']['paypal']['user_activity_page_url'] = ACTIVITY_URL


class TestGetPayPalPaymentReceipt(TestCase):
    """A pytest Test case for the GetPayPalPaymentReceipt Pipeline Step"""

    @override_settings(PAYMENT_PROCESSOR_CONFIG=TEST_PAYMENT_PROCESSOR_CONFIG)
    def test_pipeline_step(self):
        order_number = '123'
        paypal_payment_pipe = GetPayPalPaymentReceipt("test_pipe", None)

        result: dict = paypal_payment_pipe.run_filter(
            edx_lms_user_id=1,
            psp='paypal_edx',
            payment_intent_id="00001",
            order_number=order_number
        )
        url = settings.PAYMENT_PROCESSOR_CONFIG['edx']['paypal']['user_activity_page_url']
        redirect_url = f"{url}?free_text_search={order_number}"
        self.assertEqual(redirect_url, result['redirect_url'])


class RefundPayPalPaymentTests(TestCase):
    """Tests for RefundPayPalPayment pipeline step"""

    def setUp(self):
        self.refund_pipe = RefundPayPalPayment("test_pipe", None)
        self.order_id = "mock_order_id"
        self.amount_in_cents = 1000
        self.ct_transaction_interaction_id = "mock_capture_id"
        self.psp = EDX_PAYPAL_PAYMENT_INTERFACE_NAME

    @patch('commerce_coordinator.apps.paypal.clients.PayPalClient.refund_order')
    def test_refund_successful(self, mock_refund_order):
        """Test successful PayPal refund"""
        mock_refund_order.return_value = {"status": "COMPLETED"}

        ret = self.refund_pipe.run_filter(
            order_id=self.order_id,
            amount_in_cents=self.amount_in_cents,
            has_been_refunded=False,
            ct_transaction_interaction_id=self.ct_transaction_interaction_id,
            psp=self.psp,
            message_id='mock_message_id'
        )

        self.assertEqual(ret['refund_response'], {"status": "COMPLETED"})
        mock_refund_order.assert_called_once_with(capture_id=self.ct_transaction_interaction_id,
                                                  amount=self.amount_in_cents)

    def test_refund_already_refunded(self):
        """Test refund when payment has already been refunded"""
        ret = self.refund_pipe.run_filter(
            order_id=self.order_id,
            amount_in_cents=self.amount_in_cents,
            has_been_refunded=True,
            ct_transaction_interaction_id=self.ct_transaction_interaction_id,
            psp=self.psp
        )

        self.assertEqual(ret['refund_response'], "charge_already_refunded")

    def test_refund_invalid_psp(self):
        """Test refund with invalid PSP"""
        ret = self.refund_pipe.run_filter(
            order_id=self.order_id,
            amount_in_cents=self.amount_in_cents,
            has_been_refunded=False,
            ct_transaction_interaction_id=self.ct_transaction_interaction_id,
            psp="invalid_psp"
        )

        self.assertEqual(ret, PipelineCommand.CONTINUE.value)

    def test_refund_missing_amount_or_capture_id(self):
        """Test refund with missing amount or capture ID"""
        ret = self.refund_pipe.run_filter(
            order_id=self.order_id,
            amount_in_cents=None,
            has_been_refunded=False,
            ct_transaction_interaction_id=self.ct_transaction_interaction_id,
            psp=self.psp
        )

        self.assertEqual(ret, PipelineCommand.CONTINUE.value)

        ret = self.refund_pipe.run_filter(
            order_id=self.order_id,
            amount_in_cents=self.amount_in_cents,
            has_been_refunded=False,
            ct_transaction_interaction_id=None,
            psp=self.psp
        )

        self.assertEqual(ret, PipelineCommand.CONTINUE.value)

    @patch('commerce_coordinator.apps.paypal.clients.PayPalClient.refund_order')
    def test_refund_exception(self, mock_refund_order):
        """Test refund with exception raised"""
        mock_refund_order.side_effect = Exception("mock exception")

        with self.assertRaises(RequestException):
            self.refund_pipe.run_filter(
                order_id=self.order_id,
                amount_in_cents=self.amount_in_cents,
                has_been_refunded=False,
                ct_transaction_interaction_id=self.ct_transaction_interaction_id,
                psp=self.psp,
                message_id="mock_message_id"
            )
