"""
Tests for the shared CT order finalization from Stripe PaymentIntents.
"""

import datetime
from unittest.mock import MagicMock, Mock, patch

from commercetools import CommercetoolsError
from commercetools.platform.models import (
    CentPrecisionMoney,
    CustomFields,
    FieldContainer,
    Order,
    Payment,
    PaymentMethodInfo,
    PaymentState,
    Transaction,
    TransactionState,
    TransactionType,
    TypeReference,
)
from django.test import TestCase

from commerce_coordinator.apps.commercetools.stripe_payment_finalize import (
    FinalizeError,
    FinalizeResult,
    _payment_has_charge_for,
    finalize_ct_order_from_stripe_pi,
)
from commerce_coordinator.apps.commercetools.tests.conftest import (
    gen_cart,
    gen_customer,
    gen_order,
)
from commerce_coordinator.apps.core.tests.utils import uuid4_str


def _mock_pi(
    pi_id="pi_test123",
    pi_status="succeeded",
    source_system="commercetools",
    ct_cart_id="cart-uuid",
    ct_payment_id=None,
    order_id=None,
    latest_charge="ch_test456",
):
    pi = MagicMock()
    pi.id = pi_id
    pi.status = pi_status
    pi.metadata = {
        "source_system": source_system,
        "ct_cart_id": ct_cart_id,
    }
    if ct_payment_id:
        pi.metadata["ct_payment_id"] = ct_payment_id
    if order_id:
        pi.metadata["order_id"] = order_id
    pi.latest_charge = latest_charge
    return pi


def _mock_charge(charge_id="ch_test456", amount=4900, currency="usd"):
    charge = MagicMock()
    charge.id = charge_id
    charge.amount = amount
    charge.currency = currency
    charge.created = 1700000000
    return charge


def _mock_payment(payment_id=None, version=1, has_charge=False, charge_id="ch_test456"):
    txns = []
    if has_charge:
        txns.append(Transaction(
            id=uuid4_str(),
            type=TransactionType.CHARGE,
            amount=CentPrecisionMoney(cent_amount=4900, currency_code="USD", fraction_digits=2),
            state=TransactionState.SUCCESS,
            interaction_id=charge_id,
            timestamp=datetime.datetime.now(),
        ))
    return Payment(
        id=payment_id or uuid4_str(),
        version=version,
        created_at=datetime.datetime.now(),
        last_modified_at=datetime.datetime.now(),
        amount_planned=CentPrecisionMoney(cent_amount=4900, currency_code="USD", fraction_digits=2),
        payment_method_info=PaymentMethodInfo(method="upi"),
        payment_status=PaymentState.PAID,
        transactions=txns,
        interface_interactions=[],
    )


class TestPaymentHasChargeFor(TestCase):
    def test_no_transactions(self):
        payment = _mock_payment()
        self.assertFalse(_payment_has_charge_for(payment, "ch_test"))

    def test_has_matching_charge(self):
        payment = _mock_payment(has_charge=True, charge_id="ch_match")
        self.assertTrue(_payment_has_charge_for(payment, "ch_match"))

    def test_has_different_charge(self):
        payment = _mock_payment(has_charge=True, charge_id="ch_other")
        self.assertFalse(_payment_has_charge_for(payment, "ch_match"))


@patch("commerce_coordinator.apps.commercetools.stripe_payment_finalize.stripe")
@patch("commerce_coordinator.apps.commercetools.stripe_payment_finalize.track")
@patch("commerce_coordinator.apps.commercetools.stripe_payment_finalize.CommercetoolsAPIClient")
class TestFinalizeCTOrderFromStripePI(TestCase):

    def test_happy_path(self, MockClient, mock_track, mock_stripe):
        """Full finalize: charge + order + line state + segment + PI metadata."""
        pi = _mock_pi()
        charge = _mock_charge()
        mock_stripe.PaymentIntent.retrieve.return_value = pi
        mock_stripe.Charge.retrieve.return_value = charge

        payment = _mock_payment(payment_id="pay-123")
        order = gen_order(uuid4_str())
        cart = gen_cart(cart_id="cart-uuid", customer_id=order.customer_id)
        customer = gen_customer("test@example.com", "testuser")

        client = MockClient.return_value
        client.get_payment_by_key.return_value = payment
        client.create_charge_payment_transaction.return_value = payment
        client.get_order_by_payment_id.side_effect = Exception("not found")
        client.get_cart_by_id.return_value = cart
        client.create_order_from_cart.return_value = order
        client.update_line_items_transition_state.return_value = order
        client.get_customer_by_id.return_value = customer

        result = finalize_ct_order_from_stripe_pi("pi_test123", source="webhook")

        self.assertEqual(result.order_id, order.id)
        self.assertFalse(result.already_existed)
        client.create_charge_payment_transaction.assert_called_once()
        client.create_order_from_cart.assert_called_once_with(cart)
        client.update_line_items_transition_state.assert_called_once()
        mock_track.assert_called_once()

    def test_order_already_exists_skips(self, MockClient, mock_track, mock_stripe):
        """When order already exists for the payment, skip creation."""
        pi = _mock_pi()
        charge = _mock_charge()
        mock_stripe.PaymentIntent.retrieve.return_value = pi
        mock_stripe.Charge.retrieve.return_value = charge

        payment = _mock_payment(payment_id="pay-123", has_charge=True, charge_id="ch_test456")
        existing_order = gen_order(uuid4_str())

        client = MockClient.return_value
        client.get_payment_by_key.return_value = payment
        client.get_order_by_payment_id.return_value = existing_order

        result = finalize_ct_order_from_stripe_pi("pi_test123", source="webhook")

        self.assertTrue(result.already_existed)
        self.assertEqual(result.order_id, existing_order.id)
        client.create_order_from_cart.assert_not_called()
        mock_track.assert_not_called()

    def test_charge_already_present_skips_creation(self, MockClient, mock_track, mock_stripe):
        """When charge transaction already exists, don't add another."""
        pi = _mock_pi()
        charge = _mock_charge()
        mock_stripe.PaymentIntent.retrieve.return_value = pi
        mock_stripe.Charge.retrieve.return_value = charge

        payment = _mock_payment(payment_id="pay-123", has_charge=True, charge_id="ch_test456")
        order = gen_order(uuid4_str())
        cart = gen_cart(cart_id="cart-uuid", customer_id=order.customer_id)
        customer = gen_customer("test@example.com", "testuser")

        client = MockClient.return_value
        client.get_payment_by_key.return_value = payment
        client.get_order_by_payment_id.side_effect = Exception("not found")
        client.get_cart_by_id.return_value = cart
        client.create_order_from_cart.return_value = order
        client.update_line_items_transition_state.return_value = order
        client.get_customer_by_id.return_value = customer

        result = finalize_ct_order_from_stripe_pi("pi_test123", source="webhook")

        client.create_charge_payment_transaction.assert_not_called()
        self.assertFalse(result.already_existed)

    def test_pi_not_succeeded_raises_finalize_error(self, MockClient, mock_track, mock_stripe):
        pi = _mock_pi(pi_status="requires_payment_method")
        mock_stripe.PaymentIntent.retrieve.return_value = pi

        with self.assertRaises(FinalizeError) as ctx:
            finalize_ct_order_from_stripe_pi("pi_test123", source="recovery")

        self.assertIn("requires_payment_method", str(ctx.exception))

    def test_wrong_source_system_raises_finalize_error(self, MockClient, mock_track, mock_stripe):
        pi = _mock_pi(source_system="edx/commerce_coordinator?v=1")
        mock_stripe.PaymentIntent.retrieve.return_value = pi

        with self.assertRaises(FinalizeError):
            finalize_ct_order_from_stripe_pi("pi_test123", source="recovery")

    def test_missing_ct_cart_id_raises_finalize_error(self, MockClient, mock_track, mock_stripe):
        pi = _mock_pi(ct_cart_id=None)
        pi.metadata.pop("ct_cart_id", None)
        mock_stripe.PaymentIntent.retrieve.return_value = pi

        with self.assertRaises(FinalizeError):
            finalize_ct_order_from_stripe_pi("pi_test123", source="webhook")

    def test_resolves_payment_by_ct_payment_id(self, MockClient, mock_track, mock_stripe):
        """When ct_payment_id is in metadata, use it for lookup."""
        pi = _mock_pi(ct_payment_id="pay-from-meta")
        charge = _mock_charge()
        mock_stripe.PaymentIntent.retrieve.return_value = pi
        mock_stripe.Charge.retrieve.return_value = charge

        payment = _mock_payment(payment_id="pay-from-meta", has_charge=True, charge_id="ch_test456")
        existing_order = gen_order(uuid4_str())

        client = MockClient.return_value
        client.base_client.payments.get_by_id.return_value = payment
        client.get_order_by_payment_id.return_value = existing_order

        result = finalize_ct_order_from_stripe_pi("pi_test123", source="webhook")

        client.base_client.payments.get_by_id.assert_called_once_with("pay-from-meta")
        self.assertTrue(result.already_existed)

    def test_segment_event_has_web_properties(self, MockClient, mock_track, mock_stripe):
        """Segment Order Completed should have is_mobile=False and plan 18."""
        pi = _mock_pi()
        charge = _mock_charge()
        mock_stripe.PaymentIntent.retrieve.return_value = pi
        mock_stripe.Charge.retrieve.return_value = charge

        payment = _mock_payment(payment_id="pay-123")
        order = gen_order(uuid4_str())
        cart = gen_cart(cart_id="cart-uuid", customer_id=order.customer_id)
        customer = gen_customer("test@example.com", "testuser")

        client = MockClient.return_value
        client.get_payment_by_key.return_value = payment
        client.create_charge_payment_transaction.return_value = payment
        client.get_order_by_payment_id.side_effect = Exception("not found")
        client.get_cart_by_id.return_value = cart
        client.create_order_from_cart.return_value = order
        client.update_line_items_transition_state.return_value = order
        client.get_customer_by_id.return_value = customer

        finalize_ct_order_from_stripe_pi("pi_test123", source="webhook")

        call_kwargs = mock_track.call_args
        props = call_kwargs[1]["properties"] if "properties" in call_kwargs[1] else call_kwargs[0][2]
        self.assertFalse(props["is_mobile"])
        self.assertEqual(props["track_plan_id"], 18)
        self.assertEqual(props["trigger_source"], "server-side")
        self.assertEqual(props["processor_name"], "stripe")
