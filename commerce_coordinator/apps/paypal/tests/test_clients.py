"""Tests for PayPal API client."""

import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase

from commerce_coordinator.apps.paypal.clients import PayPalClient


class PayPalClientRefundOrderTests(TestCase):
    """Regression tests for refund_order request shaping."""

    @patch("commerce_coordinator.apps.paypal.clients.PaypalServersdkClient")
    @patch("commerce_coordinator.apps.paypal.clients.ApiHelper.json_serialize")
    def test_refund_order_serializes_decimal_amount_as_string(
        self, mock_json_serialize, mock_sdk_class
    ):
        """
        PayPal Money.value is a string. The refund amount may come from
        get_line_item_price_to_refund as a Decimal, and the SDK body uses
        jsonpickle, which emits null for Decimal unless we pass a string.
        """
        mock_json_serialize.return_value = json.dumps(
            {
                "id": "REFUND_ID",
                "create_time": "2024-01-01T00:00:00Z",
                "status": "COMPLETED",
                "amount": {"value": "49.00", "currency_code": "USD"},
            }
        )
        mock_payments = MagicMock()
        mock_sdk_class.return_value.payments = mock_payments

        client = PayPalClient()
        client.refund_order("CAPTURE_ID", Decimal("49.00"))

        mock_payments.refund_captured_payment.assert_called_once()
        collect = mock_payments.refund_captured_payment.call_args[0][0]
        self.assertEqual(collect["body"]["amount"]["value"], "49.00")
