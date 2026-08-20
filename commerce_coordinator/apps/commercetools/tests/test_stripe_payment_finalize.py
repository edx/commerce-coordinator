"""
Tests for the shared CT order finalization from Stripe PaymentIntents.
"""
# Class-level patch decorators inject every mock into each test method.
# pylint: disable=unused-argument

import datetime
from unittest.mock import MagicMock, patch

from commercetools import CommercetoolsError
from commercetools.platform.models import (
    CentPrecisionMoney,
    Payment,
    PaymentMethodInfo,
    PaymentState,
    Transaction,
    TransactionState,
    TransactionType
)
from django.test import TestCase

from commerce_coordinator.apps.commercetools.catalog_info.constants import TwoUKeys
from commerce_coordinator.apps.commercetools.stripe_payment_finalize import (
    FinalizeError,
    FinalizeInProgressError,
    _payment_has_charge_for,
    finalize_ct_order_from_stripe_pi
)
from commerce_coordinator.apps.commercetools.tests.conftest import gen_cart, gen_customer, gen_order
from commerce_coordinator.apps.core.tests.utils import uuid4_str


def _ct_error(code: str, message: str = "boom") -> CommercetoolsError:
    """Build a CommercetoolsError whose .code property matches production CT errors."""
    response = MagicMock()
    err_obj = MagicMock()
    err_obj.code = code
    response.errors = [err_obj]
    return CommercetoolsError(
        message=message,
        errors=[{"code": code, "message": message}],
        response=response,
        correlation_id="corr",
    )


def _stub_initial_matching_order(client, order):
    """Make get_state_by_key(Initial) match the order's first line-item state id."""
    initial = MagicMock()
    initial.id = order.line_items[0].state[0].state.id
    initial.key = TwoUKeys.INITIAL_FULFILMENT_STATE
    client.get_state_by_key.return_value = initial
    return initial


def _stub_initial_unrelated(client):
    """Initial state id that will not match order line items (already past Initial)."""
    initial = MagicMock()
    initial.id = "initial-state-id-unrelated"
    initial.key = TwoUKeys.INITIAL_FULFILMENT_STATE
    client.get_state_by_key.return_value = initial
    return initial


def _mock_pi(
    pi_id="pi_test123",
    pi_status="succeeded",
    source_system="commercetools",
    ct_cart_id="cart-uuid",
    ct_payment_id=None,
    order_id=None,
    latest_charge="ch_test456",
):
    """Build a Stripe PaymentIntent stub with CT-linking metadata."""
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
    """Build a Stripe Charge stub for the PaymentIntent's latest charge."""
    charge = MagicMock()
    charge.id = charge_id
    charge.amount = amount
    charge.currency = currency
    charge.created = 1700000000
    return charge


def _mock_payment(payment_id=None, version=1, has_charge=False, charge_id="ch_test456"):
    """Build a CT Payment, optionally already carrying a successful Charge transaction."""
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
    """Tests for Charge transaction idempotency detection on a CT payment."""

    def test_no_transactions(self):
        payment = _mock_payment()
        self.assertFalse(_payment_has_charge_for(payment, "ch_test"))

    def test_has_matching_charge(self):
        payment = _mock_payment(has_charge=True, charge_id="ch_match")
        self.assertTrue(_payment_has_charge_for(payment, "ch_match"))

    def test_has_different_charge(self):
        payment = _mock_payment(has_charge=True, charge_id="ch_other")
        self.assertFalse(_payment_has_charge_for(payment, "ch_match"))


@patch("commerce_coordinator.apps.commercetools.stripe_payment_finalize.release_task_lock")
@patch(
    "commerce_coordinator.apps.commercetools.stripe_payment_finalize.acquire_task_lock",
    return_value=True,
)
@patch("commerce_coordinator.apps.commercetools.stripe_payment_finalize.stripe")
@patch("commerce_coordinator.apps.commercetools.stripe_payment_finalize.track")
@patch("commerce_coordinator.apps.commercetools.stripe_payment_finalize.CommercetoolsAPIClient")
class TestFinalizeCTOrderFromStripePI(TestCase):
    """Tests for finalizing a CT order from a Stripe PaymentIntent."""

    def test_happy_path(self, MockClient, mock_track, mock_stripe, _mock_lock, _mock_unlock):
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
        client.get_order_by_payment_id.side_effect = ValueError("not found")
        client.get_cart_by_id.return_value = cart
        client.create_order_from_cart.return_value = order
        client.update_line_items_transition_state.return_value = order
        client.get_customer_by_id.return_value = customer
        initial = _stub_initial_matching_order(client, order)

        result = finalize_ct_order_from_stripe_pi("pi_test123", source="webhook")

        self.assertEqual(result.order_id, order.id)
        self.assertFalse(result.already_existed)
        client.create_charge_payment_transaction.assert_called_once()
        client.create_order_from_cart.assert_called_once_with(cart)
        client.get_state_by_key.assert_called_with(TwoUKeys.INITIAL_FULFILMENT_STATE)
        client.update_line_items_transition_state.assert_called_once()
        transition_kwargs = client.update_line_items_transition_state.call_args.kwargs
        self.assertEqual(transition_kwargs["from_state_id"], initial.id)
        self.assertEqual(transition_kwargs["new_state_key"], TwoUKeys.PENDING_FULFILMENT_STATE)
        mock_track.assert_called_once()
        mock_stripe.PaymentIntent.modify.assert_called_once_with(
            "pi_test123",
            metadata={
                "source_system": "commercetools",
                "ct_cart_id": "cart-uuid",
                "order_id": order.id,
                "ct_payment_id": "pay-123",
            },
        )

    def test_order_already_exists_heals_fulfillment_and_metadata(
        self, MockClient, mock_track, mock_stripe, _mock_lock, _mock_unlock
    ):
        """Existing order with Initial line items still transitions + heals PI metadata."""
        pi = _mock_pi()
        charge = _mock_charge()
        mock_stripe.PaymentIntent.retrieve.return_value = pi
        mock_stripe.Charge.retrieve.return_value = charge

        payment = _mock_payment(payment_id="pay-123", has_charge=True, charge_id="ch_test456")
        existing_order = gen_order(uuid4_str())

        client = MockClient.return_value
        client.get_payment_by_key.return_value = payment
        client.get_order_by_payment_id.return_value = existing_order
        client.update_line_items_transition_state.return_value = existing_order
        initial = _stub_initial_matching_order(client, existing_order)

        result = finalize_ct_order_from_stripe_pi("pi_test123", source="webhook")

        self.assertTrue(result.already_existed)
        self.assertEqual(result.order_id, existing_order.id)
        client.create_order_from_cart.assert_not_called()
        client.update_line_items_transition_state.assert_called_once()
        transition_kwargs = client.update_line_items_transition_state.call_args.kwargs
        self.assertEqual(transition_kwargs["from_state_id"], initial.id)
        self.assertEqual(transition_kwargs["new_state_key"], TwoUKeys.PENDING_FULFILMENT_STATE)
        mock_track.assert_not_called()
        mock_stripe.PaymentIntent.modify.assert_called_once_with(
            "pi_test123",
            metadata={
                "source_system": "commercetools",
                "ct_cart_id": "cart-uuid",
                "order_id": existing_order.id,
                "ct_payment_id": "pay-123",
            },
        )

    def test_order_already_exists_skips_transition_when_past_initial(
        self, MockClient, mock_track, mock_stripe, _mock_lock, _mock_unlock
    ):
        """When order exists and line items are past Initial, do not re-transition."""
        existing_order = gen_order(uuid4_str())
        pi = _mock_pi(order_id=existing_order.id, ct_payment_id="pay-123")
        charge = _mock_charge()
        mock_stripe.PaymentIntent.retrieve.return_value = pi
        mock_stripe.Charge.retrieve.return_value = charge

        payment = _mock_payment(payment_id="pay-123", has_charge=True, charge_id="ch_test456")

        client = MockClient.return_value
        client.base_client.payments.get_by_id.return_value = payment
        client.get_order_by_payment_id.return_value = existing_order
        _stub_initial_unrelated(client)

        result = finalize_ct_order_from_stripe_pi("pi_test123", source="webhook")

        self.assertTrue(result.already_existed)
        client.update_line_items_transition_state.assert_not_called()
        mock_stripe.PaymentIntent.modify.assert_not_called()

    def test_lock_contention_raises_in_progress(
        self, MockClient, mock_track, mock_stripe, mock_lock, _mock_unlock
    ):
        mock_lock.return_value = False
        with self.assertRaises(FinalizeInProgressError):
            finalize_ct_order_from_stripe_pi("pi_test123", source="webhook")
        MockClient.assert_not_called()

    def test_ct_outage_on_order_lookup_propagates(
        self, MockClient, mock_track, mock_stripe, _mock_lock, _mock_unlock
    ):
        """CommercetoolsError during order lookup must not be treated as not-found."""
        pi = _mock_pi()
        charge = _mock_charge()
        mock_stripe.PaymentIntent.retrieve.return_value = pi
        mock_stripe.Charge.retrieve.return_value = charge

        payment = _mock_payment(payment_id="pay-123", has_charge=True, charge_id="ch_test456")

        client = MockClient.return_value
        client.get_payment_by_key.return_value = payment
        client.get_order_by_payment_id.side_effect = _ct_error("ConcurrentModification")

        with self.assertRaises(CommercetoolsError):
            finalize_ct_order_from_stripe_pi("pi_test123", source="webhook")

        client.create_order_from_cart.assert_not_called()

    def test_order_already_exists_skips(
        self, MockClient, mock_track, mock_stripe, _mock_lock, _mock_unlock
    ):
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
        client.update_line_items_transition_state.return_value = existing_order
        _stub_initial_matching_order(client, existing_order)

        result = finalize_ct_order_from_stripe_pi("pi_test123", source="webhook")

        self.assertTrue(result.already_existed)
        self.assertEqual(result.order_id, existing_order.id)
        client.create_order_from_cart.assert_not_called()
        mock_track.assert_not_called()

    def test_create_failure_heals_when_order_appears_on_requery(
        self, MockClient, mock_track, mock_stripe, _mock_lock, _mock_unlock
    ):
        """A concurrent writer winning cart conversion is healed by authoritative re-query."""
        pi = _mock_pi()
        charge = _mock_charge()
        mock_stripe.PaymentIntent.retrieve.return_value = pi
        mock_stripe.Charge.retrieve.return_value = charge

        payment = _mock_payment(payment_id="pay-123", has_charge=True, charge_id="ch_test456")
        existing_order = gen_order(uuid4_str())
        cart = gen_cart(cart_id="cart-uuid", customer_id=existing_order.customer_id)

        client = MockClient.return_value
        client.get_payment_by_key.return_value = payment
        client.get_order_by_payment_id.side_effect = [ValueError("not found"), existing_order]
        client.get_cart_by_id.return_value = cart
        client.create_order_from_cart.side_effect = _ct_error("UnverifiedAlreadyOrderedShape")
        client.update_line_items_transition_state.return_value = existing_order
        _stub_initial_matching_order(client, existing_order)

        result = finalize_ct_order_from_stripe_pi("pi_test123", source="webhook")

        self.assertTrue(result.already_existed)
        self.assertEqual(result.order_id, existing_order.id)
        self.assertEqual(client.get_order_by_payment_id.call_count, 2)
        mock_track.assert_not_called()

    def test_create_failure_reraises_original_when_requery_is_empty(
        self, MockClient, mock_track, mock_stripe, _mock_lock, _mock_unlock
    ):
        """Unrelated create failures retain retry/quarantine behavior when no order exists."""
        pi = _mock_pi()
        charge = _mock_charge()
        mock_stripe.PaymentIntent.retrieve.return_value = pi
        mock_stripe.Charge.retrieve.return_value = charge

        payment = _mock_payment(payment_id="pay-123", has_charge=True, charge_id="ch_test456")
        cart = gen_cart(cart_id="cart-uuid")
        create_error = _ct_error("ConcurrentModification")

        client = MockClient.return_value
        client.get_payment_by_key.return_value = payment
        client.get_order_by_payment_id.side_effect = ValueError("not found")
        client.get_cart_by_id.return_value = cart
        client.create_order_from_cart.side_effect = create_error

        with self.assertRaises(CommercetoolsError) as ctx:
            finalize_ct_order_from_stripe_pi("pi_test123", source="webhook")

        self.assertIs(ctx.exception, create_error)
        self.assertEqual(client.get_order_by_payment_id.call_count, 2)
        mock_track.assert_not_called()

    def test_create_failure_propagates_requery_commercetools_error(
        self, MockClient, mock_track, mock_stripe, _mock_lock, _mock_unlock
    ):
        """A failed authoritative re-query must drive the Celery retry."""
        pi = _mock_pi()
        charge = _mock_charge()
        mock_stripe.PaymentIntent.retrieve.return_value = pi
        mock_stripe.Charge.retrieve.return_value = charge

        payment = _mock_payment(payment_id="pay-123", has_charge=True, charge_id="ch_test456")
        cart = gen_cart(cart_id="cart-uuid")
        create_error = _ct_error("InvalidOperation")
        lookup_error = _ct_error("ConcurrentModification")

        client = MockClient.return_value
        client.get_payment_by_key.return_value = payment
        client.get_order_by_payment_id.side_effect = [ValueError("not found"), lookup_error]
        client.get_cart_by_id.return_value = cart
        client.create_order_from_cart.side_effect = create_error

        with self.assertRaises(CommercetoolsError) as ctx:
            finalize_ct_order_from_stripe_pi("pi_test123", source="webhook")

        self.assertIs(ctx.exception, lookup_error)
        self.assertEqual(client.get_order_by_payment_id.call_count, 2)
        mock_track.assert_not_called()

    def test_charge_already_present_skips_creation(
        self, MockClient, mock_track, mock_stripe, _mock_lock, _mock_unlock
    ):
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
        client.get_order_by_payment_id.side_effect = ValueError("not found")
        client.get_cart_by_id.return_value = cart
        client.create_order_from_cart.return_value = order
        client.update_line_items_transition_state.return_value = order
        client.get_customer_by_id.return_value = customer
        _stub_initial_matching_order(client, order)

        result = finalize_ct_order_from_stripe_pi("pi_test123", source="webhook")

        client.create_charge_payment_transaction.assert_not_called()
        self.assertFalse(result.already_existed)

    def test_pi_not_succeeded_raises_finalize_error(
        self, MockClient, mock_track, mock_stripe, _mock_lock, _mock_unlock
    ):
        pi = _mock_pi(pi_status="requires_payment_method")
        mock_stripe.PaymentIntent.retrieve.return_value = pi

        with self.assertRaises(FinalizeError) as ctx:
            finalize_ct_order_from_stripe_pi("pi_test123", source="webhook")

        self.assertIn("requires_payment_method", str(ctx.exception))

    def test_wrong_source_system_raises_finalize_error(
        self, MockClient, mock_track, mock_stripe, _mock_lock, _mock_unlock
    ):
        pi = _mock_pi(source_system="edx/commerce_coordinator?v=1")
        mock_stripe.PaymentIntent.retrieve.return_value = pi

        with self.assertRaises(FinalizeError):
            finalize_ct_order_from_stripe_pi("pi_test123", source="webhook")

    def test_missing_ct_cart_id_raises_finalize_error(
        self, MockClient, mock_track, mock_stripe, _mock_lock, _mock_unlock
    ):
        pi = _mock_pi(ct_cart_id=None)
        pi.metadata.pop("ct_cart_id", None)
        mock_stripe.PaymentIntent.retrieve.return_value = pi

        with self.assertRaises(FinalizeError) as ctx:
            finalize_ct_order_from_stripe_pi("pi_test123", source="webhook")

        self.assertEqual(ctx.exception.ct_cart_id, "unknown")

    def test_resolves_payment_by_ct_payment_id(
        self, MockClient, mock_track, mock_stripe, _mock_lock, _mock_unlock
    ):
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
        client.update_line_items_transition_state.return_value = existing_order
        _stub_initial_matching_order(client, existing_order)

        result = finalize_ct_order_from_stripe_pi("pi_test123", source="webhook")

        client.base_client.payments.get_by_id.assert_called_once_with("pay-from-meta")
        self.assertTrue(result.already_existed)

    def test_ct_payment_id_not_found_falls_back_to_key(
        self, MockClient, mock_track, mock_stripe, _mock_lock, _mock_unlock
    ):
        """ResourceNotFound on metadata.ct_payment_id falls back to PI key lookup."""
        pi = _mock_pi(ct_payment_id="pay-stale")
        charge = _mock_charge()
        mock_stripe.PaymentIntent.retrieve.return_value = pi
        mock_stripe.Charge.retrieve.return_value = charge

        payment = _mock_payment(payment_id="pay-by-key", has_charge=True, charge_id="ch_test456")
        existing_order = gen_order(uuid4_str())

        client = MockClient.return_value
        client.base_client.payments.get_by_id.side_effect = _ct_error("ResourceNotFound")
        client.get_payment_by_key.return_value = payment
        client.get_order_by_payment_id.return_value = existing_order
        client.update_line_items_transition_state.return_value = existing_order
        _stub_initial_matching_order(client, existing_order)

        result = finalize_ct_order_from_stripe_pi("pi_test123", source="webhook")

        client.get_payment_by_key.assert_called_once_with("pi_test123")
        self.assertTrue(result.already_existed)

    def test_ct_payment_id_transient_error_propagates(
        self, MockClient, mock_track, mock_stripe, _mock_lock, _mock_unlock
    ):
        """Non-not-found CommercetoolsError on ct_payment_id lookup must not fall back."""
        pi = _mock_pi(ct_payment_id="pay-from-meta")
        mock_stripe.PaymentIntent.retrieve.return_value = pi

        client = MockClient.return_value
        client.base_client.payments.get_by_id.side_effect = _ct_error("ConcurrentModification")

        with self.assertRaises(CommercetoolsError):
            finalize_ct_order_from_stripe_pi("pi_test123", source="webhook")

        client.get_payment_by_key.assert_not_called()

    def test_segment_event_has_web_properties(
        self, MockClient, mock_track, mock_stripe, _mock_lock, _mock_unlock
    ):
        """Segment Order Completed should have is_mobile=False, plan 18, payment_method=upi."""
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
        client.get_order_by_payment_id.side_effect = ValueError("not found")
        client.get_cart_by_id.return_value = cart
        client.create_order_from_cart.return_value = order
        client.update_line_items_transition_state.return_value = order
        client.get_customer_by_id.return_value = customer
        _stub_initial_matching_order(client, order)

        finalize_ct_order_from_stripe_pi("pi_test123", source="webhook")

        call_kwargs = mock_track.call_args
        props = call_kwargs[1]["properties"] if "properties" in call_kwargs[1] else call_kwargs[0][2]
        self.assertFalse(props["is_mobile"])
        self.assertEqual(props["track_plan_id"], 18)
        self.assertEqual(props["trigger_source"], "server-side")
        self.assertEqual(props["processor_name"], "stripe")
        self.assertEqual(props["payment_method"], "upi")
