"""State-aware Stripe refund reconciliation for CommerceTools payments."""

import logging
from dataclasses import dataclass

from commercetools.platform.models import ReturnPaymentState, TransactionState
from django.utils.module_loading import import_string
from edx_django_utils.cache import TieredCache
from iso4217 import Currency

from commerce_coordinator.apps.commercetools.catalog_info.edx_utils import check_is_bundle, get_edx_lms_user_id
from commerce_coordinator.apps.commercetools.catalog_info.utils import get_product_data
from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient, Refund
from commerce_coordinator.apps.commercetools.utils import (
    convert_ct_cent_amount_to_localized_price,
    get_refund_transaction_by_interaction_id,
    prepare_segment_event_properties
)
from commerce_coordinator.apps.core.memcache import safe_key
from commerce_coordinator.apps.core.segment import track
from commerce_coordinator.apps.core.signal_helpers import format_signal_results
from commerce_coordinator.apps.core.tasks import acquire_task_lock, release_task_lock
from commerce_coordinator.apps.stripe.constants import StripeRefundStatus

logger = logging.getLogger(__name__)

REFUND_RECONCILE_LOCK_PREFIX = "reconcile_stripe_refund"
REFUND_RECONCILE_LOCK_EXPIRE = 300
REFUND_SIDE_EFFECT_CACHE_PREFIX = "stripe_refund_side_effect"
REFUND_SIDE_EFFECT_CACHE_TTL_SECS = 60 * 60 * 24 * 7

STRIPE_TO_CT_STATE = {
    StripeRefundStatus.REFUND_PENDING.value: TransactionState.PENDING,
    StripeRefundStatus.REFUND_SUCCESS.value: TransactionState.SUCCESS,
    StripeRefundStatus.REFUND_FAILED.value: TransactionState.FAILURE,
    StripeRefundStatus.REFUND_CANCELED.value: TransactionState.FAILURE,
}


class RefundReconcileInProgressError(Exception):
    """Another worker is reconciling the same Stripe refund."""


class RefundSideEffectDispatchError(Exception):
    """A refund side effect could not be dispatched safely."""


@dataclass
class RefundReconcileResult:
    """Outcome of a refund reconciliation attempt."""

    payment_id: str | None
    refund_id: str
    transaction_state: TransactionState | None
    side_effects_completed: bool = False
    return_found: bool = False


def refund_reconcile_lock_key(refund_id: str) -> str:
    """Build the shared lock key used by webhook admission and workers."""
    return safe_key(
        key=refund_id,
        key_prefix=REFUND_RECONCILE_LOCK_PREFIX,
        version="1",
    )


def reconcile_stripe_refund(
    payment_intent_id: str,
    stripe_refund: Refund,
    *,
    order_number: str | None = None,
    source: str,
    client: CommercetoolsAPIClient | None = None,
) -> RefundReconcileResult:
    """Reconcile one Stripe Refund under a lock keyed by Stripe Refund ID."""
    refund_id = stripe_refund["id"]
    target_state = STRIPE_TO_CT_STATE.get(stripe_refund.get("status"))
    if target_state is None:
        logger.warning(
            "[stripe_refund_reconcile] Ignoring refund %s with unknown status %s",
            refund_id,
            stripe_refund.get("status"),
        )
        return RefundReconcileResult(None, refund_id, None)

    lock_key = refund_reconcile_lock_key(refund_id)
    if not acquire_task_lock(lock_key, REFUND_RECONCILE_LOCK_EXPIRE):
        raise RefundReconcileInProgressError(
            f"Refund reconciliation already in progress for {refund_id}"
        )

    try:
        return _reconcile_stripe_refund_locked(
            payment_intent_id,
            stripe_refund,
            target_state=target_state,
            order_number=order_number,
            source=source,
            client=client,
        )
    finally:
        release_task_lock(lock_key)


def _reconcile_stripe_refund_locked(
    payment_intent_id: str,
    stripe_refund: Refund,
    *,
    target_state: TransactionState,
    order_number: str | None,
    source: str,
    client: CommercetoolsAPIClient | None,
) -> RefundReconcileResult:
    """Reconcile body; the caller holds the refund-ID lock."""
    if client is None:
        client = CommercetoolsAPIClient()

    refund_id = stripe_refund["id"]
    payment = client.get_payment_by_key(payment_intent_id)
    transaction = get_refund_transaction_by_interaction_id(payment, refund_id)
    from_state = transaction.state if transaction else None

    if transaction is None:
        payment = client.create_return_payment_transaction(
            payment_id=payment.id,
            payment_version=payment.version,
            refund=stripe_refund,
        )
        transaction = get_refund_transaction_by_interaction_id(payment, refund_id)
    elif _can_transition(transaction.state, target_state):
        payment = client.change_refund_transaction_state(
            payment_id=payment.id,
            payment_version=payment.version,
            transaction_id=transaction.id,
            state=target_state,
        )
        transaction = get_refund_transaction_by_interaction_id(payment, refund_id)

    if transaction is None or _state_value(transaction.state) != _state_value(target_state):
        logger.warning(
            "[stripe_refund_reconcile] Ignoring conflicting terminal state for refund %s: "
            "ct_state=%s stripe_target=%s",
            refund_id,
            transaction.state if transaction else None,
            target_state,
        )
        return RefundReconcileResult(
            payment.id,
            refund_id,
            transaction.state if transaction else None,
        )

    logger.info(
        "[stripe_refund_reconcile] payment=%s stripe_refund_id=%s source=%s "
        "from_state=%s to_state=%s",
        payment.id,
        refund_id,
        source,
        from_state,
        target_state,
    )

    order = _find_order(client, payment.id, order_number)
    if order is None:
        logger.warning(
            "[stripe_refund_reconcile] Refund %s reached %s without a CT order; "
            "payment transaction updated only",
            refund_id,
            target_state,
        )
        return RefundReconcileResult(payment.id, refund_id, target_state)

    return_items = _resolve_return_items(order, transaction)
    if not return_items:
        logger.warning(
            "[stripe_refund_reconcile] Refund %s reached %s with no CT Return; "
            "payment transaction updated only",
            refund_id,
            target_state,
        )
        return RefundReconcileResult(payment.id, refund_id, target_state)

    result = RefundReconcileResult(
        payment.id,
        refund_id,
        target_state,
        return_found=True,
    )
    if target_state == TransactionState.PENDING:
        _update_return_state(
            client,
            order,
            payment,
            return_items,
            stripe_refund,
            payment_intent_id=payment_intent_id,
            should_transition_state=False,
        )
        logger.info(
            "[stripe_refund_reconcile] Refund %s remains pending; no LMS or Segment side effects",
            refund_id,
        )
        return result

    if target_state == TransactionState.FAILURE:
        if not _all_in_payment_state(return_items, ReturnPaymentState.NOT_REFUNDED):
            _update_return_state(
                client,
                order,
                payment,
                return_items,
                stripe_refund,
                payment_intent_id=payment_intent_id,
                payment_state=ReturnPaymentState.NOT_REFUNDED,
            )
        logger.warning(
            "[stripe_refund_reconcile] Refund %s failed; LMS access preserved and Segment suppressed",
            refund_id,
        )
        return result

    revoke_completed = _side_effect_completed(refund_id, "lms_revoke")
    segment_completed = _side_effect_completed(refund_id, "segment")
    if not _all_in_payment_state(return_items, ReturnPaymentState.REFUNDED):
        _update_return_state(
            client,
            order,
            payment,
            return_items,
            stripe_refund,
            payment_intent_id=payment_intent_id,
            payment_state=ReturnPaymentState.REFUNDED,
        )

    if revoke_completed and segment_completed:
        logger.info(
            "[stripe_refund_reconcile] Refund %s side effects already completed",
            refund_id,
        )
        result.side_effects_completed = True
        return result

    if not revoke_completed:
        _dispatch_revoke(order.id, return_items)
        _mark_side_effect_completed(refund_id, "lms_revoke")
    if not segment_completed:
        _emit_segment_refund(client, order, stripe_refund, return_items)
        _mark_side_effect_completed(refund_id, "segment")
    result.side_effects_completed = True
    logger.info(
        "[stripe_refund_reconcile] Refund %s completed lms_revoke=true segment_emitted=true",
        refund_id,
    )
    return result


def _state_value(state):
    return getattr(state, "value", state)


def _can_transition(current_state, target_state: TransactionState) -> bool:
    """Allow only Pending to terminal transitions; never regress terminal CT state."""
    current = _state_value(current_state)
    target = _state_value(target_state)
    if current == target:
        return False
    return current == TransactionState.PENDING.value and target in {
        TransactionState.SUCCESS.value,
        TransactionState.FAILURE.value,
    }


def _find_order(client, payment_id: str, order_number: str | None):
    """Find the order by explicit number or its attached CT payment."""
    try:
        if order_number:
            return client.get_order_by_number(order_number)
        return client.get_order_by_payment_id(payment_id)
    except ValueError:
        return None


def _resolve_return_items(order, transaction) -> list:
    """Resolve return items from the transaction marker or open CT returns."""
    all_return_items = [
        item
        for return_info in (order.return_info or [])
        for item in return_info.items
    ]
    custom = getattr(transaction, "custom", None)
    fields = getattr(custom, "fields", {}) if custom else {}
    return_item_ids = {
        item_id.strip()
        for item_id in (fields.get("returnItemId", "") or "").split(",")
        if item_id.strip()
    }
    if return_item_ids:
        return [item for item in all_return_items if item.id in return_item_ids]
    return [
        item
        for item in all_return_items
        if item.payment_state == ReturnPaymentState.INITIAL
    ]


def _all_in_payment_state(return_items, payment_state: ReturnPaymentState) -> bool:
    return all(item.payment_state == payment_state for item in return_items)


def _side_effect_cache_key(refund_id: str, side_effect: str) -> str:
    return safe_key(
        key=f"{refund_id}_{side_effect}",
        key_prefix=REFUND_SIDE_EFFECT_CACHE_PREFIX,
        version="1",
    )


def _side_effect_completed(refund_id: str, side_effect: str) -> bool:
    cache_key = _side_effect_cache_key(refund_id, side_effect)
    return TieredCache.get_cached_response(cache_key).is_found


def _mark_side_effect_completed(refund_id: str, side_effect: str) -> None:
    cache_key = _side_effect_cache_key(refund_id, side_effect)
    TieredCache.set_all_tiers(
        cache_key,
        value="COMPLETED",
        django_cache_timeout=REFUND_SIDE_EFFECT_CACHE_TTL_SECS,
    )


def _return_item_payload(return_items) -> list[dict]:
    return [
        {"id": item.id, "lineItemId": item.line_item_id}
        for item in return_items
    ]


def _dispatch_revoke(order_id: str, return_items) -> None:
    """Dispatch the existing retryable LMS revoke task through its signal."""
    revoke_signal = import_string(
        "commerce_coordinator.apps.commercetools.signals."
        "fulfill_order_returned_send_revoke_line_items_signal"
    )

    results = revoke_signal.send_robust(
        sender=reconcile_stripe_refund,
        order_id=order_id,
        return_items=_return_item_payload(return_items),
    )
    formatted = format_signal_results(results)
    if not results or any(entry["error"] for entry in formatted.values()):
        raise RefundSideEffectDispatchError(
            f"Unable to dispatch LMS revoke for order {order_id}: {formatted}"
        )


def _emit_segment_refund(client, order, stripe_refund: Refund, return_items) -> None:
    """Emit the existing Order Refunded Segment payload for selected returns."""
    customer = client.get_customer_by_id(order.customer_id)
    lms_user_id = get_edx_lms_user_id(customer)
    line_item_ids = {item.line_item_id for item in return_items}
    selected_line_items = [
        item for item in order.line_items if item.id in line_item_ids
    ]
    fraction_digits = Currency(stripe_refund["currency"].upper()).exponent
    total = convert_ct_cent_amount_to_localized_price(
        stripe_refund["amount"],
        fraction_digits,
    )
    properties = prepare_segment_event_properties(
        order=order,
        total_in_dollars=str(total),
        line_item_ids=list(line_item_ids),
        return_id=", ".join(item.id for item in return_items),
    )
    is_bundle = check_is_bundle(order.line_items)
    properties["products"] = [
        get_product_data(item, is_bundle) for item in selected_line_items
    ]
    if not properties["products"]:
        raise RefundSideEffectDispatchError(
            f"Unable to emit Order Refunded for refund {stripe_refund['id']}: "
            "no matching line items to include as products"
        )
    properties["title"] = ", ".join(
        item.name["en-US"] for item in selected_line_items
    )
    track(
        lms_user_id=lms_user_id,
        event="Order Refunded",
        properties=properties,
        message_id=stripe_refund["id"],
    )


def _update_return_state(
    client,
    order,
    payment,
    return_items,
    stripe_refund,
    *,
    payment_intent_id: str | None = None,
    payment_state: ReturnPaymentState = ReturnPaymentState.REFUNDED,
    should_transition_state: bool = True,
):
    """Persist the CT return state and refund-to-return custom markers."""
    return_item_ids = [item.id for item in return_items]
    return client.update_return_payment_state_after_successful_refund(
        order_id=order.id,
        order_version=order.version,
        return_line_item_return_ids=return_item_ids,
        return_line_entitlement_ids={},
        refunded_line_item_refunds={},
        payment_intent_id=stripe_refund.get("payment_intent") or payment_intent_id or "",
        interaction_id=stripe_refund["id"],
        payment_state=payment_state,
        payment=payment,
        should_transition_state=should_transition_state,
    )
