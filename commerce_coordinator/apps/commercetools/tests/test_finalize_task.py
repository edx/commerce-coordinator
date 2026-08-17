"""
Tests for the finalize_commercetools_stripe_payment_task Celery task.
"""
# Celery's bind=True self argument is supplied by the task decorator.
# pylint: disable=no-value-for-parameter

from unittest.mock import patch

from django.test import TestCase

from commerce_coordinator.apps.commercetools.stripe_payment_finalize import (
    FinalizeError,
    FinalizeInProgressError,
    FinalizeResult
)
from commerce_coordinator.apps.commercetools.tasks import finalize_commercetools_stripe_payment_task

FINALIZE_PATH = "commerce_coordinator.apps.commercetools.tasks.finalize_ct_order_from_stripe_pi"


class TestFinalizeTask(TestCase):
    """Tests for the Celery task wrapping the shared Stripe/CT finalize path."""

    @patch(FINALIZE_PATH)
    def test_happy_path_returns_order_id(self, mock_finalize):
        mock_finalize.return_value = FinalizeResult(
            order_id="order-123",
            order_number="2U-2026000001",
            payment_id="pay-456",
        )

        result = finalize_commercetools_stripe_payment_task("pi_test")
        self.assertEqual(result, "order-123")
        mock_finalize.assert_called_once_with("pi_test", source="webhook")

    @patch(FINALIZE_PATH)
    def test_already_existed_returns_order_id(self, mock_finalize):
        mock_finalize.return_value = FinalizeResult(
            order_id="order-existing",
            order_number="2U-2026000002",
            payment_id="pay-789",
            already_existed=True,
        )

        result = finalize_commercetools_stripe_payment_task("pi_test")
        self.assertEqual(result, "order-existing")

    @patch(FINALIZE_PATH)
    @patch("commerce_coordinator.apps.commercetools.tasks._log_quarantine")
    def test_finalize_error_quarantines_and_returns_none(
        self, mock_quarantine, mock_finalize
    ):
        mock_finalize.side_effect = FinalizeError("missing ct_cart_id")

        result = finalize_commercetools_stripe_payment_task("pi_bad")
        self.assertIsNone(result)
        mock_quarantine.assert_called_once()
        call_kwargs = mock_quarantine.call_args[1]
        self.assertEqual(call_kwargs["pi_id"], "pi_bad")
        self.assertEqual(call_kwargs["source"], "webhook")
        self.assertIn("missing ct_cart_id", call_kwargs["reason"])

    @patch(FINALIZE_PATH)
    @patch("commerce_coordinator.apps.commercetools.tasks._log_quarantine")
    def test_unexpected_error_quarantines_and_reraises(
        self, mock_quarantine, mock_finalize
    ):
        mock_finalize.side_effect = RuntimeError("boom")

        with self.assertRaises(RuntimeError):
            finalize_commercetools_stripe_payment_task("pi_boom")

        mock_quarantine.assert_called_once()

    @patch.object(finalize_commercetools_stripe_payment_task, "apply_async")
    @patch(FINALIZE_PATH)
    def test_lock_contention_reschedules(self, mock_finalize, mock_apply_async):
        mock_finalize.side_effect = FinalizeInProgressError("locked")

        result = finalize_commercetools_stripe_payment_task("pi_busy")

        self.assertIsNone(result)
        mock_apply_async.assert_called_once()
        call_kwargs = mock_apply_async.call_args.kwargs
        self.assertEqual(call_kwargs["kwargs"]["payment_intent_id"], "pi_busy")
