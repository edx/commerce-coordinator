"""
Shared finalization logic for CommerceTools orders originating from Stripe
PaymentIntents (UPI webhook).

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
    get_product_from_line_item
)
from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient
from commerce_coordinator.apps.core.memcache import safe_key
from commerce_coordinator.apps.core.segment import track
from commerce_coordinator.apps.core.tasks import acquire_task_lock, release_task_lock

logger = logging.getLogger(__name__)

FINALIZE_LOCK_PREFIX = "finalize_ct_order_from_stripe_pi"
# Default lock TTL is 60s; this path can exceed that under CT latency.
# 5 minutes covers a slow run without pinning a crashed worker for 30 minutes.
FINALIZE_LOCK_EXPIRE = 300


class FinalizeError(Exception):
    """Non-retryable finalization error (quarantine candidate)."""

    def __init__(
        self,
        message: str,
        *,
        ct_payment_id: str = "unknown",
        ct_cart_id: str = "unknown",
    ):
        super().__init__(message)
        self.ct_payment_id = ct_payment_id or "unknown"
        self.ct_cart_id = ct_cart_id or "unknown"


class FinalizeInProgressError(Exception):
    """Another worker holds the finalize lock for this PI."""


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


def _backfill_pi_metadata(
    payment_intent_id: str,
    order_id: str,
    payment_id: str,
    *,
    existing_metadata: dict | None = None,
) -> None:
    """
    Write order_id / ct_payment_id onto the Stripe PaymentIntent (idempotent).

    Merges with existing metadata so keys like source_system / ct_cart_id are preserved
    even if Stripe treats metadata as a full replacement.
    """
    try:
        merged = dict(existing_metadata or {})
        merged["order_id"] = order_id
        merged["ct_payment_id"] = payment_id
        stripe.PaymentIntent.modify(
            payment_intent_id,
            metadata=merged,
        )
    except Exception:  # pylint: disable=broad-exception-caught
        logger.warning(
            "[finalize_ct_order] Failed to backfill PI metadata for %s",
            payment_intent_id,
            exc_info=True,
        )


def _discount_amount_dollars(cart) -> float:
    """Extract cart-level discount as dollars from CT cart shapes."""
    discount_on_total = getattr(cart, "discount_on_total_price", None)
    if not discount_on_total:
        return 0

    discounted_amount = getattr(discount_on_total, "discounted_amount", None)
    if discounted_amount is not None:
        return cents_to_dollars(discounted_amount)

    # Fallback if a money-like object was passed directly (tests / older shapes)
    if hasattr(discount_on_total, "cent_amount"):
        return cents_to_dollars(discount_on_total)

    return 0


def _line_item_has_state_id(line_item, state_id: str) -> bool:
    """True if any ItemState on the line item references the given state ID."""
    for item_state in (getattr(line_item, "state", None) or []):
        ref = getattr(item_state, "state", None)
        if ref is not None and getattr(ref, "id", None) == state_id:
            return True
    return False


def _ensure_pending_fulfilment(client, order):
    """
    Transition line items still in Initial → PENDING_FULFILMENT.

    Uses TwoUKeys.INITIAL_FULFILMENT_STATE (looked up by key) as from_state so we do
    not depend on line_items[0].state[0], which is fragile on partial-success retries.
    """
    if not order.line_items:
        logger.warning(
            "[finalize_ct_order] Order %s has no line items; cannot transition fulfillment",
            order.id,
        )
        return order

    initial_state = client.get_state_by_key(TwoUKeys.INITIAL_FULFILMENT_STATE)
    items_needing_transition = [
        item for item in order.line_items
        if _line_item_has_state_id(item, initial_state.id)
    ]
    if not items_needing_transition:
        logger.info(
            "[finalize_ct_order] Order %s line items already past Initial; skipping transition",
            order.id,
        )
        return order

    return client.update_line_items_transition_state(
        order_id=order.id,
        order_version=order.version,
        line_items=items_needing_transition,
        from_state_id=initial_state.id,
        new_state_key=TwoUKeys.PENDING_FULFILMENT_STATE,
        use_state_id=True,
    )


def _heal_existing_order(client, order, payment_intent_id, payment, metadata):
    """Heal fulfillment and PI metadata without re-emitting analytics."""
    _ensure_pending_fulfilment(client, order)
    if not metadata.get("order_id") or metadata.get("ct_payment_id") != payment.id:
        _backfill_pi_metadata(
            payment_intent_id,
            order.id,
            payment.id,
            existing_metadata=metadata,
        )
    return FinalizeResult(
        order_id=order.id,
        order_number=order.order_number or "",
        payment_id=payment.id,
        already_existed=True,
    )


def finalize_ct_order_from_stripe_pi(
    payment_intent_id: str,
    *,
    source: str,
    client: CommercetoolsAPIClient | None = None,
) -> FinalizeResult:
    """
    Shared finalize path used by the webhook Celery task.

    Steps (parity with customer-twou finalizeStripePayment):
      1. Retrieve / validate Stripe PaymentIntent
      2. Resolve CT Payment (by key = pi.id or metadata.ct_payment_id)
      3. Resolve CT Cart (by metadata.ct_cart_id)
      4. Add Charge transaction if absent (idempotent by interaction_id)
      5. If order already exists: heal PENDING_FULFILMENT + PI metadata, return
      6. Create order from cart → COMPLETE / PAID / SHIPPED
      7. Transition line items → PENDING_FULFILMENT (from Initial by key)
      8. Emit Segment Order Completed (plan 18, is_mobile=False)
      9. Backfill PI metadata with order_id + ct_payment_id

    Args:
        payment_intent_id: Stripe PaymentIntent ID
        source: quarantine log context (typically 'webhook')
        client: Optional pre-built CT client (avoids re-init in loops)

    Returns:
        FinalizeResult with order details

    Raises:
        FinalizeError: on non-retryable problems (missing metadata, etc.)
        FinalizeInProgressError: when another writer holds the PI finalize lock
        CommercetoolsError: on transient CT failures (retryable by caller)
    """
    lock_key = safe_key(
        key=payment_intent_id,
        key_prefix=FINALIZE_LOCK_PREFIX,
        version="1",
    )
    if not acquire_task_lock(lock_key, FINALIZE_LOCK_EXPIRE):
        raise FinalizeInProgressError(
            f"Finalize already in progress for PaymentIntent {payment_intent_id}"
        )

    try:
        return _finalize_ct_order_from_stripe_pi_locked(
            payment_intent_id, source=source, client=client,
        )
    finally:
        release_task_lock(lock_key)


def _finalize_ct_order_from_stripe_pi_locked(
    payment_intent_id: str,
    *,
    source: str,
    client: CommercetoolsAPIClient | None = None,
) -> FinalizeResult:
    """Finalize body; caller holds the PI lock."""
    if client is None:
        client = CommercetoolsAPIClient()

    pi = stripe.PaymentIntent.retrieve(payment_intent_id)
    metadata = pi.metadata or {}

    if pi.status != "succeeded":
        raise FinalizeError(
            f"PaymentIntent {payment_intent_id} status is '{pi.status}', expected 'succeeded'",
            ct_cart_id=metadata.get("ct_cart_id", "unknown"),
            ct_payment_id=metadata.get("ct_payment_id", "unknown"),
        )

    if metadata.get("source_system") != "commercetools":
        raise FinalizeError(
            f"PaymentIntent {payment_intent_id} source_system is "
            f"'{metadata.get('source_system')}', expected 'commercetools'",
            ct_cart_id=metadata.get("ct_cart_id", "unknown"),
            ct_payment_id=metadata.get("ct_payment_id", "unknown"),
        )

    ct_cart_id = metadata.get("ct_cart_id")
    if not ct_cart_id:
        raise FinalizeError(
            f"PaymentIntent {payment_intent_id} missing metadata.ct_cart_id",
            ct_payment_id=metadata.get("ct_payment_id", "unknown"),
        )

    ct_payment_id_from_meta = metadata.get("ct_payment_id")

    # --- Resolve CT Payment ---
    if ct_payment_id_from_meta:
        try:
            payment = client.base_client.payments.get_by_id(ct_payment_id_from_meta)
        except CommercetoolsError as err:
            # Only fall back on true not-found; re-raise transient CT failures for retry.
            if err.code != "ResourceNotFound":
                raise
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
    # ValueError = not found (aligned with client docstring). CommercetoolsError must
    # propagate so Celery can retry instead of creating a duplicate order.
    try:
        existing_order = client.get_order_by_payment_id(payment.id)
    except ValueError:
        existing_order = None

    if existing_order is not None:
        logger.info(
            "[finalize_ct_order] Order %s already exists for payment %s (pi=%s), "
            "skipping creation; healing PENDING_FULFILMENT and PI metadata",
            existing_order.id, payment.id, payment_intent_id,
        )
        return _heal_existing_order(
            client, existing_order, payment_intent_id, payment, metadata,
        )

    # --- Load cart and create order ---
    cart = client.get_cart_by_id(ct_cart_id)
    try:
        order = client.create_order_from_cart(cart)
    except CommercetoolsError as create_error:
        try:
            existing_order = client.get_order_by_payment_id(payment.id)
        except (ValueError, CommercetoolsError):
            existing_order = None
        if existing_order is None:
            raise create_error
        logger.info(
            "[finalize_ct_order] Order %s appeared after create failed for payment %s; healing",
            existing_order.id, payment.id,
        )
        return _heal_existing_order(
            client, existing_order, payment_intent_id, payment, metadata,
        )

    # --- Transition line items → PENDING_FULFILMENT ---
    order = _ensure_pending_fulfilment(client, order)

    # --- Emit Segment Order Completed (plan 18, web) ---
    _emit_web_order_completed(client, order, cart, payment)

    # --- Backfill PI metadata ---
    _backfill_pi_metadata(
        payment_intent_id,
        order.id,
        payment.id,
        existing_metadata=metadata,
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
        if payment.payment_method_info and payment.payment_method_info.method:
            payment_method = payment.payment_method_info.method

        discount_codes = getattr(cart, "discount_codes", []) or []
        discount_code = None
        coupon_name = []
        if discount_codes:
            codes_as_dicts = []
            for dc in discount_codes:
                code_obj = getattr(dc, "discount_code", None)
                if code_obj is not None and hasattr(code_obj, "obj") and code_obj.obj:
                    codes_as_dicts.append({"code": getattr(code_obj.obj, "code", None)})
                elif hasattr(dc, "code"):
                    codes_as_dicts.append({"code": dc.code})
                elif isinstance(dc, dict) and "code" in dc:
                    codes_as_dicts.append(dc)
            codes_as_dicts = [d for d in codes_as_dicts if d.get("code")]
            if codes_as_dicts:
                discount_code = codes_as_dicts[-1].get("code")
                coupon_name = [
                    d["code"] for d in codes_as_dicts[:-1]
                    if d.get("code")
                ]

        taxed_amount = 0
        if order.taxed_price and order.taxed_price.total_tax:
            taxed_amount = cents_to_dollars(order.taxed_price.total_tax)

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
            "discount": _discount_amount_dollars(cart),
            "payment_method": payment_method,
            "processor_name": "stripe",
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
    except Exception:  # pylint: disable=broad-exception-caught
        logger.warning(
            "[finalize_ct_order] Failed to emit Segment Order Completed for order %s",
            order.id, exc_info=True,
        )
