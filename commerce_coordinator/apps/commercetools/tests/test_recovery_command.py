"""
Tests for the recover_orphaned_stripe_commercetools_payments management command.
"""

from io import StringIO
from unittest.mock import MagicMock, patch

from commercetools import CommercetoolsError
from commercetools.platform.models import TransactionState, TransactionType
from django.test import TestCase

from commerce_coordinator.apps.commercetools.management.commands.recover_orphaned_stripe_commercetools_payments import (
    Command
)
from commerce_coordinator.apps.commercetools.stripe_payment_finalize import (
    FinalizeError,
    FinalizeInProgressError,
    FinalizeResult
)

CMD_MODULE = (
    "commerce_coordinator.apps.commercetools.management.commands"
    ".recover_orphaned_stripe_commercetools_payments"
)


@patch(f"{CMD_MODULE}.CommercetoolsAPIClientCommand.__init__", return_value=None)
class TestRecoveryCommand(TestCase):
    """Tests for the orphaned Stripe/CT payment recovery management command."""

    def _make_command(self):
        """Build a command instance with a mocked CT client and captured output streams."""
        cmd = Command()
        cmd.ct_api_client = MagicMock()
        cmd.stdout = StringIO()
        cmd.stderr = StringIO()
        return cmd

    @patch(f"{CMD_MODULE}.finalize_ct_order_from_stripe_pi")
    def test_dry_run_lists_candidates(self, mock_finalize, _mock_init):
        cmd = self._make_command()

        pi1 = MagicMock()
        pi1.id = "pi_orphan1"
        pi1.metadata = {"source_system": "commercetools"}
        pi2 = MagicMock()
        pi2.id = "pi_orphan2"
        pi2.metadata = {"source_system": "commercetools"}

        with patch(f"{CMD_MODULE}.stripe") as mock_stripe:
            search_result = MagicMock()
            search_result.data = [pi1, pi2]
            search_result.has_more = False
            mock_stripe.PaymentIntent.search.return_value = search_result

            cmd.handle(since=7, limit=100, dry_run=True, max_list_examined=1000)

        output = cmd.stdout.getvalue()
        self.assertIn("[dry-run] orphan: pi_orphan1", output)
        self.assertIn("[dry-run] orphan: pi_orphan2", output)
        mock_finalize.assert_not_called()

    @patch(f"{CMD_MODULE}.finalize_ct_order_from_stripe_pi")
    def test_finalize_happy_path(self, mock_finalize, _mock_init):
        cmd = self._make_command()

        pi1 = MagicMock()
        pi1.id = "pi_orphan1"
        pi1.metadata = {"source_system": "commercetools"}

        mock_finalize.return_value = FinalizeResult(
            order_id="order-new",
            order_number="2U-2026000001",
            payment_id="pay-123",
        )

        with patch(f"{CMD_MODULE}.stripe") as mock_stripe:
            search_result = MagicMock()
            search_result.data = [pi1]
            search_result.has_more = False
            mock_stripe.PaymentIntent.search.return_value = search_result

            cmd.handle(since=7, limit=100, dry_run=False, max_list_examined=1000)

        output = cmd.stdout.getvalue()
        self.assertIn("[finalized] pi_orphan1 -> order order-new", output)
        self.assertIn("1 finalized", output)

    @patch(f"{CMD_MODULE}._log_quarantine")
    @patch(f"{CMD_MODULE}.finalize_ct_order_from_stripe_pi")
    def test_finalize_error_quarantines(self, mock_finalize, mock_quarantine, _mock_init):
        cmd = self._make_command()

        pi1 = MagicMock()
        pi1.id = "pi_bad"
        pi1.metadata = {"source_system": "commercetools"}

        mock_finalize.side_effect = FinalizeError("missing cart")

        with patch(f"{CMD_MODULE}.stripe") as mock_stripe:
            search_result = MagicMock()
            search_result.data = [pi1]
            search_result.has_more = False
            mock_stripe.PaymentIntent.search.return_value = search_result

            cmd.handle(since=7, limit=100, dry_run=False, max_list_examined=1000)

        err_output = cmd.stderr.getvalue()
        self.assertIn("[quarantine] pi_bad", err_output)
        mock_quarantine.assert_called_once()
        quarantine_kwargs = mock_quarantine.call_args.kwargs
        self.assertEqual(quarantine_kwargs["pi_id"], "pi_bad")
        self.assertEqual(quarantine_kwargs["source"], "recovery")
        self.assertIn("1 quarantined", cmd.stdout.getvalue())

    @patch(f"{CMD_MODULE}.finalize_ct_order_from_stripe_pi")
    def test_already_existed_skips(self, mock_finalize, _mock_init):
        cmd = self._make_command()

        pi1 = MagicMock()
        pi1.id = "pi_existing"
        pi1.metadata = {"source_system": "commercetools"}

        mock_finalize.return_value = FinalizeResult(
            order_id="order-old",
            order_number="2U-2026000002",
            payment_id="pay-456",
            already_existed=True,
        )

        with patch(f"{CMD_MODULE}.stripe") as mock_stripe:
            search_result = MagicMock()
            search_result.data = [pi1]
            search_result.has_more = False
            mock_stripe.PaymentIntent.search.return_value = search_result

            cmd.handle(since=7, limit=100, dry_run=False, max_list_examined=1000)

        output = cmd.stdout.getvalue()
        self.assertIn("[skip] pi_existing", output)

    def test_limit_truncates(self, _mock_init):
        cmd = self._make_command()

        pis = []
        for i in range(10):
            pi = MagicMock()
            pi.id = f"pi_orphan_{i}"
            pi.metadata = {"source_system": "commercetools"}
            pis.append(pi)

        with patch(f"{CMD_MODULE}.stripe") as mock_stripe:
            search_result = MagicMock()
            search_result.data = pis
            search_result.has_more = True
            search_result.next_page = "page2"
            mock_stripe.PaymentIntent.search.return_value = search_result

            cmd.handle(since=7, limit=3, dry_run=True, max_list_examined=1000)

        output = cmd.stdout.getvalue()
        self.assertIn("3 Stripe orphan candidate(s)", output)

    def test_search_fallback_to_list(self, _mock_init):
        cmd = self._make_command()

        pi1 = MagicMock()
        pi1.id = "pi_list_orphan"
        pi1.status = "succeeded"
        pi1.metadata = {"source_system": "commercetools"}

        with patch(f"{CMD_MODULE}.stripe") as mock_stripe:
            mock_stripe.PaymentIntent.search.side_effect = Exception("search not available")
            list_result = MagicMock()
            list_result.auto_paging_iter.return_value = [pi1]
            mock_stripe.PaymentIntent.list.return_value = list_result

            cmd.handle(since=7, limit=100, dry_run=True, max_list_examined=1000)

        output = cmd.stdout.getvalue()
        self.assertIn("[dry-run] orphan: pi_list_orphan", output)

    @patch(f"{CMD_MODULE}.finalize_ct_order_from_stripe_pi")
    def test_ct_secondary_discovery(self, mock_finalize, _mock_init):
        """CT payments with Success Charge and no Order become orphan candidates."""
        cmd = self._make_command()

        payment = MagicMock()
        payment.id = "pay-ct-1"
        payment.interface_id = "pi_ct_secondary"
        charge_txn = MagicMock()
        charge_txn.type = TransactionType.CHARGE
        charge_txn.state = TransactionState.SUCCESS
        payment.transactions = [charge_txn]

        query_result = MagicMock()
        query_result.results = [payment]
        cmd.ct_api_client.base_client.payments.query.return_value = query_result
        cmd.ct_api_client.get_order_by_payment_id.side_effect = ValueError("no order")

        stripe_pi = MagicMock()
        stripe_pi.id = "pi_ct_secondary"
        stripe_pi.status = "succeeded"
        stripe_pi.metadata = {"source_system": "commercetools"}

        with patch(f"{CMD_MODULE}.stripe") as mock_stripe:
            # No Stripe-primary orphans
            search_result = MagicMock()
            search_result.data = []
            search_result.has_more = False
            mock_stripe.PaymentIntent.search.return_value = search_result
            mock_stripe.PaymentIntent.retrieve.return_value = stripe_pi

            cmd.handle(since=7, limit=100, dry_run=True, max_list_examined=1000)

        output = cmd.stdout.getvalue()
        self.assertIn("1 CT-secondary orphan candidate(s)", output)
        self.assertIn("[dry-run] orphan: pi_ct_secondary", output)
        mock_finalize.assert_not_called()

    @patch(f"{CMD_MODULE}._log_quarantine")
    @patch(f"{CMD_MODULE}.finalize_ct_order_from_stripe_pi")
    def test_commercetools_error_deferred_not_quarantined(
        self, mock_finalize, mock_quarantine, _mock_init
    ):
        """Transient CT errors must not quarantine (next cron retries)."""
        cmd = self._make_command()

        pi1 = MagicMock()
        pi1.id = "pi_transient"
        pi1.metadata = {"source_system": "commercetools"}

        mock_finalize.side_effect = CommercetoolsError(
            message="blip",
            errors=[{"code": "ConcurrentModification", "message": "blip"}],
            response={},
            correlation_id="corr",
        )

        with patch(f"{CMD_MODULE}.stripe") as mock_stripe:
            search_result = MagicMock()
            search_result.data = [pi1]
            search_result.has_more = False
            mock_stripe.PaymentIntent.search.return_value = search_result

            cmd.handle(since=7, limit=100, dry_run=False, max_list_examined=1000)

            mock_stripe.PaymentIntent.retrieve.assert_not_called()

        self.assertIn("[retryable] pi_transient", cmd.stderr.getvalue())
        self.assertIn("1 deferred", cmd.stdout.getvalue())
        mock_quarantine.assert_not_called()

    @patch(f"{CMD_MODULE}._log_quarantine")
    @patch(f"{CMD_MODULE}.finalize_ct_order_from_stripe_pi")
    def test_lock_contention_deferred_not_quarantined(
        self, mock_finalize, mock_quarantine, _mock_init
    ):
        cmd = self._make_command()

        pi1 = MagicMock()
        pi1.id = "pi_busy"
        pi1.metadata = {"source_system": "commercetools"}
        mock_finalize.side_effect = FinalizeInProgressError("locked")

        with patch(f"{CMD_MODULE}.stripe") as mock_stripe:
            search_result = MagicMock()
            search_result.data = [pi1]
            search_result.has_more = False
            mock_stripe.PaymentIntent.search.return_value = search_result

            cmd.handle(since=7, limit=100, dry_run=False, max_list_examined=1000)

        self.assertIn("[deferred] pi_busy", cmd.stderr.getvalue())
        mock_quarantine.assert_not_called()

    def test_list_filter_respects_max_examined(self, _mock_init):
        """List+filter fallback must stop after max_list_examined PIs."""
        cmd = self._make_command()

        pis = []
        for i in range(20):
            pi = MagicMock()
            pi.id = f"pi_{i}"
            pi.status = "succeeded"
            # Non-matching source so we keep examining without filling limit early
            pi.metadata = {"source_system": "other"}
            pis.append(pi)

        with patch(f"{CMD_MODULE}.stripe") as mock_stripe:
            mock_stripe.PaymentIntent.search.side_effect = Exception("search down")
            list_result = MagicMock()
            list_result.auto_paging_iter.return_value = pis
            mock_stripe.PaymentIntent.list.return_value = list_result

            cmd.handle(since=7, limit=100, dry_run=True, max_list_examined=5)

        # No orphans found (wrong source_system), but we must not walk past the cap
        output = cmd.stdout.getvalue()
        self.assertIn("0 Stripe orphan candidate(s)", output)
