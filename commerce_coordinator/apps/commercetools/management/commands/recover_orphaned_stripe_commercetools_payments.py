"""
Management command to discover and finalize orphaned Stripe PaymentIntents
that have source_system=commercetools, status=succeeded, but no order_id
in their metadata.

Intended to run on an external cron (e.g. every 15-30 minutes).
"""

import datetime
import logging
import time

import stripe
from commercetools import CommercetoolsError
from django.conf import settings

from commerce_coordinator.apps.commercetools.management.commands._ct_api_client_command import (
    CommercetoolsAPIClientCommand,
)
from commerce_coordinator.apps.commercetools.stripe_payment_finalize import (
    FinalizeError,
    finalize_ct_order_from_stripe_pi,
)
from commerce_coordinator.apps.commercetools.tasks import _log_quarantine

logger = logging.getLogger(__name__)

stripe.api_key = settings.PAYMENT_PROCESSOR_CONFIG['edx']['stripe']['secret_key']


class Command(CommercetoolsAPIClientCommand):
    help = (
        "Discover orphaned Stripe PaymentIntents (succeeded, source_system=commercetools, "
        "no order_id) and finalize them into CT orders. Supports --since, --limit, --dry-run."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--since",
            type=int,
            default=7,
            help="Lookback window in days (default: 7)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=100,
            help="Maximum number of orphan candidates to process per run (default: 100)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="List orphan candidates without calling finalize",
        )

    def handle(self, *args, **options):
        since_days = options["since"]
        limit = options["limit"]
        dry_run = options["dry_run"]

        created_after = int(
            (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=since_days)).timestamp()
        )

        self.stdout.write(
            f"Recovery: since={since_days}d limit={limit} dry_run={dry_run}"
        )

        orphans = self._discover_stripe_orphans(created_after, limit)
        self.stdout.write(f"Discovered {len(orphans)} Stripe orphan candidate(s)")

        if dry_run:
            for pi_id in orphans:
                self.stdout.write(f"  [dry-run] orphan: {pi_id}")
            return

        finalized = 0
        quarantined = 0

        for pi_id in orphans:
            try:
                result = finalize_ct_order_from_stripe_pi(
                    pi_id, source="recovery", client=self.ct_api_client,
                )
                if result.already_existed:
                    self.stdout.write(
                        f"  [skip] {pi_id} -> order {result.order_id} already existed"
                    )
                else:
                    self.stdout.write(
                        f"  [finalized] {pi_id} -> order {result.order_id}"
                    )
                    finalized += 1
            except FinalizeError as exc:
                self.stderr.write(f"  [quarantine] {pi_id}: {exc}")
                _log_quarantine(
                    pi_id=pi_id,
                    ct_payment_id="unknown",
                    ct_cart_id="unknown",
                    reason=str(exc),
                    source="recovery",
                )
                quarantined += 1
            except (CommercetoolsError, Exception) as exc:
                self.stderr.write(f"  [quarantine] {pi_id}: {exc}")
                _log_quarantine(
                    pi_id=pi_id,
                    ct_payment_id="unknown",
                    ct_cart_id="unknown",
                    reason=str(exc),
                    source="recovery",
                )
                quarantined += 1

        self.stdout.write(
            f"Recovery complete: {finalized} finalized, {quarantined} quarantined, "
            f"{len(orphans) - finalized - quarantined} skipped"
        )

    def _discover_stripe_orphans(self, created_after: int, limit: int) -> list[str]:
        """
        Query Stripe for PaymentIntents that are succeeded with
        source_system=commercetools but missing order_id metadata.

        Uses Stripe Search API with fallback to list+filter.
        """
        orphan_ids = []

        try:
            orphan_ids = self._search_stripe_orphans(created_after, limit)
        except Exception:
            logger.warning(
                "[recovery] Stripe Search API failed, falling back to list+filter",
                exc_info=True,
            )
            orphan_ids = self._list_filter_stripe_orphans(created_after, limit)

        return orphan_ids

    def _search_stripe_orphans(self, created_after: int, limit: int) -> list[str]:
        """Use Stripe Search API to find orphaned PIs."""
        query = (
            f"status:'succeeded' "
            f"AND metadata['source_system']:'commercetools' "
            f"AND created>{created_after}"
        )

        orphan_ids = []
        has_more = True
        next_page = None

        while has_more and len(orphan_ids) < limit:
            kwargs = {"query": query, "limit": min(100, limit - len(orphan_ids))}
            if next_page:
                kwargs["page"] = next_page

            result = stripe.PaymentIntent.search(**kwargs)

            for pi in result.data:
                metadata = pi.metadata or {}
                if not metadata.get("order_id"):
                    orphan_ids.append(pi.id)
                    if len(orphan_ids) >= limit:
                        break

            has_more = result.has_more
            next_page = result.next_page if has_more else None

        if has_more and len(orphan_ids) >= limit:
            logger.info(
                "[recovery] Stripe search truncated at limit=%d, more candidates may exist",
                limit,
            )

        return orphan_ids

    def _list_filter_stripe_orphans(self, created_after: int, limit: int) -> list[str]:
        """Fallback: list PIs and filter client-side."""
        orphan_ids = []

        params = {
            "limit": 100,
            "created": {"gte": created_after},
        }

        for pi in stripe.PaymentIntent.list(**params).auto_paging_iter():
            if pi.status != "succeeded":
                continue

            metadata = pi.metadata or {}
            if metadata.get("source_system") != "commercetools":
                continue

            if not metadata.get("order_id"):
                orphan_ids.append(pi.id)

            if len(orphan_ids) >= limit:
                logger.info(
                    "[recovery] List+filter truncated at limit=%d", limit,
                )
                break

        return orphan_ids
