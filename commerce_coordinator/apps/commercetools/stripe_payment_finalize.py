"""
Shared finalization logic for CommerceTools orders originating from Stripe
PaymentIntents (UPI webhook + orphan recovery).

Parity source: customer-twou finalizeStripePayment + runPostPaymentActions.
"""

import datetime
import logging
from dataclasses import dataclass

import stripe
from commercetools import CommercetoolsError
from commercetools.platform.models import TransactionType

from commerce_coordinator.apps.commercetools.catalog_info.constants import TwoUKeys
from commerce_coordinator.apps.commercetools.catalog_info.edx_utils import (
    cents_to_dollars,
    get_edx_lms_user_id,
    get_product_from_line_item,
)
from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient
from commerce_coordinator.apps.core.segment import track

logger = logging.getLogger(__name__)


class FinalizeError(Exception):
    """Non-retryable finalization error (quarantine candidate)."""


@dataclass
class FinalizeResult:
    order_id: str
    order_number: str
    payment_id: str
    already_existed: bool = False


def _payment_has_charge_for(payment, charge_id: str) -> bool:
    """Check whether the CT payment already has a Charge txn for this charge."""
    if not payment.transactions:
        return False
    return any(
        t.type == TransactionType.CHARGE and t.interaction_id == charge_id
        for t in payment.transactions
    )


def finalize_ct_order_from_stripe_pi(
    payment_intent_id: str,
    *,
    source: str,
    client: CommercetoolsAPIClient | None = None,
) -> FinalizeResult:
    """
    Shared finalize path used by both the webhook Celery task and the
    recovery management command.

    Steps (parity with customer-twou finalizeStripePayment):
      1. Retrieve / validate Stripe PaymentIntent
      2. Resolve CT Payment (by key = pi.id or metadata.ct_payment_id)
      3. Resolve CT Cart (by metadata.ct_cart_id)
      4. Add Charge transaction if absent (idempotent by interaction_id)
      5. Skip if order already exists for this payment
      6. Create order from cart → COMPLETE / PAID / SHIPPED
      7. Transition line items → PENDING_FULFILMENT
      8. Emit Segment Order Completed (plan 18, is_mobile=False)
      9. Backfill PI metadata with order_id + ct_payment_id

    Args:
        payment_intent_id: Stripe PaymentIntent ID
        source: 'webhook' or 'recovery' (for quarantine log context)
        client: Optional pre-built CT client (avoids re-init in loops)

    Returns:
        FinalizeResult with order details

    Raises:
        FinalizeError: on non-retryable problems (missing metadata, etc.)
        CommercetoolsError: on transient CT failures (retryable by caller)
    """
    if client is None:
        client = CommercetoolsAPIClient()

    pi = stripe.PaymentIntent.retrieve(payment_intent_id)

    if pi.status != "succeeded":
        raise FinalizeError(
            f"PaymentIntent {payment_intent_id} status is '{pi.status}', expected 'succeeded'"
        )

    metadata = pi.metadata or {}
    if metadata.get("source_system") != "commercetools":
        raise FinalizeError(
            f"PaymentIntent {payment_intent_id} source_system is "
            f"'{metadata.get('source_system')}', expected 'commercetools'"
        )

    ct_cart_id = metadata.get("ct_cart_id")
    if not ct_cart_id:
        raise FinalizeError(
            f"PaymentIntent {payment_intent_id} missing metadata.ct_cart_id"
        )

    ct_payment_id_from_meta = metadata.get("ct_payment_id")

    # --- Resolve CT Payment ---
    if ct_payment_id_from_meta:
        try:
            payment = client.base_client.payments.get_by_id(ct_payment_id_from_meta)
        except CommercetoolsError:
            logger.warning(
                "[finalize_ct_order] ct_payment_id %s from metadata not found, "
                "falling back to key lookup for pi %s",
                ct_payment_id_from_meta, payment_intent_id,
            )
            payment = client.get_payment_by_key(payment_intent_id)
    else:
        payment = client.get_payment_by_key(payment_intent_id)

    # --- Add Charge transaction if absent ---
    latest_charge = pi.latest_charge
    if latest_charge and isinstance(latest_charge, str):
        latest_charge = stripe.Charge.retrieve(latest_charge)

    if latest_charge and not _payment_has_charge_for(payment, latest_charge.id):
        payment = client.create_charge_payment_transaction(
            payment_id=payment.id,
            payment_version=payment.version,
            charge_id=latest_charge.id,
            amount_in_cents=latest_charge.amount,
            currency_code=latest_charge.currency,
            charge_created=datetime.datetime.fromtimestamp(
                latest_charge.created, tz=datetime.timezone.utc
            ),
        )
        logger.info(
            "[finalize_ct_order] Added Charge txn for pi=%s charge=%s",
            payment_intent_id, latest_charge.id,
        )

    # --- Check if order already exists ---
    try:
        existing_order = client.get_order_by_payment_id(payment.id)
        logger.info(
            "[finalize_ct_order] Order %s already exists for payment %s (pi=%s), skipping creation",
            existing_order.id, payment.id, payment_intent_id,
        )
        return FinalizeResult(
            order_id=existing_order.id,
            order_number=existing_order.order_number or "",
            payment_id=payment.id,
            already_existed=True,
        )
    except Exception:
        pass

    # --- Load cart and create order ---
    cart = client.get_cart_by_id(ct_cart_id)
    order = client.create_order_from_cart(cart)

    # --- Transition line items → PENDING_FULFILMENT ---
    order = client.update_line_items_transition_state(
        order_id=order.id,
        order_version=order.version,
        line_items=order.line_items,
        from_state_id=order.line_items[0].state[0].state.id,
        new_state_key=TwoUKeys.PENDING_FULFILMENT_STATE,
        use_state_id=True,
    )

    # --- Emit Segment Order Completed (plan 18, web) ---
    _emit_web_order_completed(client, order, cart, payment)

    # --- Backfill PI metadata ---
    try:
        stripe.PaymentIntent.modify(
            payment_intent_id,
            metadata={
                "order_id": order.id,
                "ct_payment_id": payment.id,
            },
        )
    except Exception:
        logger.warning(
            "[finalize_ct_order] Failed to backfill PI metadata for %s",
            payment_intent_id, exc_info=True,
        )

    logger.info(
        "[finalize_ct_order] Successfully finalized order %s for pi=%s source=%s",
        order.id, payment_intent_id, source,
    )

    return FinalizeResult(
        order_id=order.id,
        order_number=order.order_number or "",
        payment_id=payment.id,
    )


def _emit_web_order_completed(client, order, cart, payment):
    """Emit Segment 'Order Completed' event for the web/UPI path (plan 18)."""
    try:
        customer = client.get_customer_by_id(order.customer_id)
        lms_user_id = get_edx_lms_user_id(customer)

        standalone_price = cart.total_price
        products = [
            get_product_from_line_item(item, standalone_price)
            for item in cart.line_items
        ]

        payment_method = "unknown"
        processor_name = "stripe"
        if payment.payment_method_info:
            payment_method = payment.payment_method_info.method or "unknown"
            if payment.payment_method_info.name:
                processor_name = payment.payment_method_info.name.get("en", "stripe")

        discount_codes = getattr(cart, "discount_codes", []) or []
        discount_code = None
        coupon_name = []
        if discount_codes:
            codes_as_dicts = []
            for dc in discount_codes:
                if hasattr(dc, "code"):
                    codes_as_dicts.append({"code": dc.code})
                elif isinstance(dc, dict) and "code" in dc:
                    codes_as_dicts.append(dc)
            if codes_as_dicts:
                discount_code = codes_as_dicts[-1].get("code")
                coupon_name = [
                    d["code"] for d in codes_as_dicts[:-1]
                    if d.get("code")
                ]

        taxed_amount = 0
        if order.taxed_price and order.taxed_price.total_tax:
            taxed_amount = cents_to_dollars(order.taxed_price.total_tax)

        discount_amount = 0
        if cart.discount_on_total_price:
            discount_amount = cents_to_dollars(cart.discount_on_total_price)

        event_props = {
            "track_plan_id": 18,
            "trigger_source": "server-side",
            "order_id": order.id,
            "checkout_id": cart.id,
            "currency": standalone_price.currency_code,
            "total": cents_to_dollars(standalone_price),
            "tax": taxed_amount,
            "coupon": discount_code,
            "coupon_name": coupon_name,
            "discount": discount_amount,
            "payment_method": payment_method,
            "processor_name": processor_name,
            "products": products,
            "is_mobile": False,
            "multi_item_cart_enabled": len(cart.line_items) > 1,
        }

        track(
            lms_user_id=lms_user_id,
            event="Order Completed",
            properties=event_props,
        )
        logger.info(
            "[finalize_ct_order] Emitted Segment Order Completed for order %s, user %s",
            order.id, lms_user_id,
        )
    except Exception:
        logger.warning(
            "[finalize_ct_order] Failed to emit Segment Order Completed for order %s",
            order.id, exc_info=True,
        )
