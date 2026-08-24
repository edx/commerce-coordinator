"""Tests for state-aware Stripe refund reconciliation."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from commercetools.platform.models import ReturnPaymentState, TransactionState, TransactionType
from edx_django_utils.cache import TieredCache

from commerce_coordinator.apps.commercetools.stripe_refund_reconcile import (
    _emit_segment_refund,
    _side_effect_cache_key,
    reconcile_stripe_refund
)


def _refund(status="succeeded"):
    return {
        "id": "re_async",
        "payment_intent": "pi_async",
        "amount": 4900,
        "currency": "usd",
        "created": 1692942318,
        "status": status,
    }


def _transaction(state):
    return SimpleNamespace(
        id="txn_refund",
        interaction_id="re_async",
        type=TransactionType.REFUND,
        state=state,
        custom=SimpleNamespace(fields={"returnItemId": "return-1"}),
    )


def _payment(transaction=None):
    return SimpleNamespace(
        id="payment-1",
        version=3,
        transactions=[transaction] if transaction else [],
    )


def _order(payment_state=ReturnPaymentState.INITIAL):
    return SimpleNamespace(
        id="order-1",
        order_number="2U-123",
        return_info=[
            SimpleNamespace(
                items=[
                    SimpleNamespace(
                        id="return-1",
                        line_item_id="line-1",
                        payment_state=payment_state,
                    )
                ]
            )
        ],
    )


@pytest.fixture(autouse=True)
def clear_refund_side_effect_cache():
    """Keep per-refund completion markers isolated between tests."""
    cache_keys = [
        _side_effect_cache_key("re_async", "lms_revoke"),
        _side_effect_cache_key("re_async", "segment"),
    ]
    for cache_key in cache_keys:
        TieredCache.delete_all_tiers(cache_key)
    yield
    for cache_key in cache_keys:
        TieredCache.delete_all_tiers(cache_key)


@patch("commerce_coordinator.apps.commercetools.stripe_refund_reconcile.release_task_lock")
@patch("commerce_coordinator.apps.commercetools.stripe_refund_reconcile.acquire_task_lock", return_value=True)
@patch("commerce_coordinator.apps.commercetools.stripe_refund_reconcile._update_return_state")
@patch("commerce_coordinator.apps.commercetools.stripe_refund_reconcile._emit_segment_refund")
@patch("commerce_coordinator.apps.commercetools.stripe_refund_reconcile._dispatch_revoke")
class TestStripeRefundReconcile:
    """Exercise refund state transitions and the shared side-effect gate."""

    def test_pending_creates_pending_without_terminal_side_effects(
        self,
        mock_revoke,
        mock_segment,
        mock_update_return,
        _mock_acquire,
        _mock_release,
    ):
        client = MagicMock()
        client.get_payment_by_key.return_value = _payment()
        pending_transaction = _transaction(TransactionState.PENDING)
        client.create_return_payment_transaction.return_value = _payment(pending_transaction)
        client.get_order_by_payment_id.return_value = _order()

        result = reconcile_stripe_refund(
            "pi_async",
            _refund("pending"),
            source="webhook",
            client=client,
        )

        client.create_return_payment_transaction.assert_called_once()
        mock_update_return.assert_called_once()
        assert mock_update_return.call_args.kwargs["should_transition_state"] is False
        mock_revoke.assert_not_called()
        mock_segment.assert_not_called()
        assert result.transaction_state == TransactionState.PENDING

    @pytest.mark.parametrize(
        ("stripe_status", "expected_state"),
        [
            ("failed", TransactionState.FAILURE),
            ("canceled", TransactionState.FAILURE),
        ],
    )
    def test_failure_updates_pending_and_preserves_access(
        self,
        mock_revoke,
        mock_segment,
        mock_update_return,
        _mock_acquire,
        _mock_release,
        stripe_status,
        expected_state,
    ):
        client = MagicMock()
        pending = _transaction(TransactionState.PENDING)
        failed = _transaction(TransactionState.FAILURE)
        client.get_payment_by_key.return_value = _payment(pending)
        client.change_refund_transaction_state.return_value = _payment(failed)
        client.get_order_by_payment_id.return_value = _order()

        result = reconcile_stripe_refund(
            "pi_async",
            _refund(stripe_status),
            source="webhook",
            client=client,
        )

        client.change_refund_transaction_state.assert_called_once_with(
            payment_id="payment-1",
            payment_version=3,
            transaction_id="txn_refund",
            state=expected_state,
        )
        assert mock_update_return.call_args.kwargs["payment_state"] == ReturnPaymentState.NOT_REFUNDED
        mock_revoke.assert_not_called()
        mock_segment.assert_not_called()
        assert result.transaction_state == expected_state

    def test_pending_to_success_records_refunded_before_side_effects(
        self,
        mock_revoke,
        mock_segment,
        mock_update_return,
        _mock_acquire,
        _mock_release,
    ):
        client = MagicMock()
        pending = _transaction(TransactionState.PENDING)
        succeeded = _transaction(TransactionState.SUCCESS)
        client.get_payment_by_key.return_value = _payment(pending)
        client.change_refund_transaction_state.return_value = _payment(succeeded)
        client.get_order_by_payment_id.return_value = _order()
        call_order = []
        mock_update_return.side_effect = lambda *args, **kwargs: call_order.append("update")
        mock_revoke.side_effect = lambda *args, **kwargs: call_order.append("revoke")
        mock_segment.side_effect = lambda *args, **kwargs: call_order.append("segment")

        result = reconcile_stripe_refund(
            "pi_async",
            _refund(),
            source="webhook",
            client=client,
        )

        assert call_order == ["update", "revoke", "segment"]
        assert mock_update_return.call_args.kwargs["payment_state"] == ReturnPaymentState.REFUNDED
        assert result.side_effects_completed is True

    def test_return_update_failure_does_not_emit_side_effects(
        self,
        mock_revoke,
        mock_segment,
        mock_update_return,
        _mock_acquire,
        _mock_release,
    ):
        client = MagicMock()
        pending = _transaction(TransactionState.PENDING)
        succeeded = _transaction(TransactionState.SUCCESS)
        client.get_payment_by_key.return_value = _payment(pending)
        client.change_refund_transaction_state.return_value = _payment(succeeded)
        client.get_order_by_payment_id.return_value = _order()
        mock_update_return.side_effect = RuntimeError("ct write failed")

        with pytest.raises(RuntimeError):
            reconcile_stripe_refund(
                "pi_async",
                _refund(),
                source="webhook",
                client=client,
            )

        mock_revoke.assert_not_called()
        mock_segment.assert_not_called()

        mock_update_return.side_effect = None
        result = reconcile_stripe_refund(
            "pi_async",
            _refund(),
            source="webhook",
            client=client,
        )

        mock_revoke.assert_called_once()
        mock_segment.assert_called_once()
        assert result.side_effects_completed is True

    def test_already_refunded_dispatches_unmarked_side_effects(
        self,
        mock_revoke,
        mock_segment,
        mock_update_return,
        _mock_acquire,
        _mock_release,
    ):
        client = MagicMock()
        client.get_payment_by_key.return_value = _payment(_transaction(TransactionState.SUCCESS))
        client.get_order_by_payment_id.return_value = _order(ReturnPaymentState.REFUNDED)

        result = reconcile_stripe_refund(
            "pi_async",
            _refund(),
            source="webhook",
            client=client,
        )

        client.change_refund_transaction_state.assert_not_called()
        mock_update_return.assert_not_called()
        mock_revoke.assert_called_once()
        mock_segment.assert_called_once()
        assert result.side_effects_completed is True

    def test_existing_success_with_incomplete_side_effects_heals(
        self,
        mock_revoke,
        mock_segment,
        mock_update_return,
        _mock_acquire,
        _mock_release,
    ):
        client = MagicMock()
        client.get_payment_by_key.return_value = _payment(_transaction(TransactionState.SUCCESS))
        client.get_order_by_payment_id.return_value = _order(ReturnPaymentState.INITIAL)

        reconcile_stripe_refund(
            "pi_async",
            _refund(),
            source="forward",
            client=client,
        )

        mock_revoke.assert_called_once()
        mock_segment.assert_called_once()
        mock_update_return.assert_called_once()

    def test_forward_success_then_webhook_does_not_duplicate_side_effects(
        self,
        mock_revoke,
        mock_segment,
        mock_update_return,
        _mock_acquire,
        _mock_release,
    ):
        client = MagicMock()
        return_order = _order(ReturnPaymentState.INITIAL)
        client.get_payment_by_key.return_value = _payment(_transaction(TransactionState.SUCCESS))
        client.get_order_by_payment_id.return_value = return_order

        reconcile_stripe_refund(
            "pi_async",
            _refund(),
            source="forward",
            client=client,
        )
        return_order.return_info[0].items[0].payment_state = ReturnPaymentState.REFUNDED
        reconcile_stripe_refund(
            "pi_async",
            _refund(),
            source="webhook",
            client=client,
        )

        mock_revoke.assert_called_once()
        mock_segment.assert_called_once()
        mock_update_return.assert_called_once()

    def test_partial_side_effect_completion_only_heals_missing_effect(
        self,
        mock_revoke,
        mock_segment,
        mock_update_return,
        _mock_acquire,
        _mock_release,
    ):
        client = MagicMock()
        client.get_payment_by_key.return_value = _payment(_transaction(TransactionState.SUCCESS))
        client.get_order_by_payment_id.return_value = _order(ReturnPaymentState.REFUNDED)
        TieredCache.set_all_tiers(
            _side_effect_cache_key("re_async", "lms_revoke"),
            value="COMPLETED",
            django_cache_timeout=60,
        )

        result = reconcile_stripe_refund(
            "pi_async",
            _refund(),
            source="webhook",
            client=client,
        )

        mock_revoke.assert_not_called()
        mock_segment.assert_called_once()
        mock_update_return.assert_not_called()
        assert result.side_effects_completed is True

    def test_unknown_status_does_not_default_to_success(
        self,
        mock_revoke,
        mock_segment,
        mock_update_return,
        mock_acquire,
        _mock_release,
    ):
        client = MagicMock()

        result = reconcile_stripe_refund(
            "pi_async",
            _refund("requires_action"),
            source="webhook",
            client=client,
        )

        client.get_payment_by_key.assert_not_called()
        mock_acquire.assert_not_called()
        mock_revoke.assert_not_called()
        mock_segment.assert_not_called()
        mock_update_return.assert_not_called()
        assert result.transaction_state is None


@patch("commerce_coordinator.apps.commercetools.stripe_refund_reconcile.track")
@patch("commerce_coordinator.apps.commercetools.stripe_refund_reconcile.get_edx_lms_user_id", return_value="lms-1")
def test_segment_uses_stripe_refund_id_as_message_id(_mock_lms_id, mock_track):
    client = MagicMock()
    client.get_customer_by_id.return_value = SimpleNamespace(id="cust-1")
    order = SimpleNamespace(
        id="order-1",
        customer_id="cust-1",
        line_items=[
            SimpleNamespace(
                id="line-1",
                name={"en-US": "Course"},
                product_key="course-1",
                product_type=SimpleNamespace(obj=SimpleNamespace(name="course")),
                variant=SimpleNamespace(sku="sku", images=[], attributes=[]),
                price=SimpleNamespace(value=SimpleNamespace(cent_amount=4900, currency_code="USD", fraction_digits=2)),
                quantity=1,
            )
        ],
        return_info=[],
        custom=None,
        total_price=SimpleNamespace(cent_amount=4900, currency_code="USD"),
        taxed_price=None,
        discount_on_total_price=None,
        discount_codes=[],
        payment_info=None,
    )

    with patch(
        "commerce_coordinator.apps.commercetools.stripe_refund_reconcile.prepare_segment_event_properties",
        return_value={"products": []},
    ) as mock_props:
        mock_props.return_value = {"products": [{"name": "Course"}]}
        with patch(
            "commerce_coordinator.apps.commercetools.stripe_refund_reconcile.get_product_data",
            return_value={"name": "Course"},
        ):
            with patch(
                "commerce_coordinator.apps.commercetools.stripe_refund_reconcile.check_is_bundle",
                return_value=False,
            ):
                _emit_segment_refund(
                    client,
                    order,
                    _refund(),
                    [SimpleNamespace(id="return-1", line_item_id="line-1")],
                )

    mock_track.assert_called_once()
    assert mock_track.call_args.kwargs["message_id"] == "re_async"
    assert mock_track.call_args.kwargs["event"] == "Order Refunded"
