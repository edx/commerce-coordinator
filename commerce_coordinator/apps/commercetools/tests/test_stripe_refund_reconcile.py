"""Tests for state-aware Stripe refund reconciliation."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from commercetools.platform.models import ReturnPaymentState, TransactionState, TransactionType

from commerce_coordinator.apps.commercetools.stripe_refund_reconcile import reconcile_stripe_refund


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

    def test_pending_to_success_runs_side_effects_then_records_refunded(
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

        result = reconcile_stripe_refund(
            "pi_async",
            _refund(),
            source="webhook",
            client=client,
        )

        mock_revoke.assert_called_once()
        mock_segment.assert_called_once()
        assert mock_update_return.call_args.kwargs["payment_state"] == ReturnPaymentState.REFUNDED
        assert result.side_effects_completed is True

    def test_duplicate_success_uses_refunded_return_as_completion_marker(
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
        mock_revoke.assert_not_called()
        mock_segment.assert_not_called()
        mock_update_return.assert_not_called()
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
