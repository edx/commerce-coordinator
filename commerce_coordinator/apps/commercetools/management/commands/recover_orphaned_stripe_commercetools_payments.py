"""
Management command to discover and finalize orphaned Stripe PaymentIntents /
CommerceTools Payments that have succeeded without a linked Order.

Discovery:
  1. Stripe primary — succeeded PIs with source_system=commercetools and no order_id
  2. CT secondary — stripe_edx payments with a Success Charge and no Order

Intended to run on an external cron (e.g. every 15-30 minutes).
"""

import datetime
import logging

import stripe
from commercetools import CommercetoolsError
from commercetools.platform.models import TransactionState, TransactionType
from django.conf import settings

from commerce_coordinator.apps.commercetools.catalog_info.constants import (
    EDX_STRIPE_PAYMENT_INTERFACE_NAME,
)
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
        "Discover orphaned Stripe PaymentIntents / CT Payments (succeeded, "
        "source_system=commercetools / stripe_edx, no Order) and finalize them. "
        "Supports --since, --limit, --dry-run."
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
        created_after_iso = datetime.datetime.fromtimestamp(
            created_after, tz=datetime.timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%S.000Z")

        self.stdout.write(
            f"Recovery: since={since_days}d limit={limit} dry_run={dry_run}"
        )

        stripe_orphans = self._discover_stripe_orphans(created_after, limit)
        self.stdout.write(f"Discovered {len(stripe_orphans)} Stripe orphan candidate(s)")

        remaining = max(0, limit - len(stripe_orphans))
        ct_orphans = []
        if remaining > 0:
            ct_orphans = self._discover_ct_orphans(
                created_after_iso, remaining, set(stripe_orphans),
            )
            self.stdout.write(f"Discovered {len(ct_orphans)} CT-secondary orphan candidate(s)")

        orphans = stripe_orphans + ct_orphans

        if dry_run:
            for pi_id in orphans:
                self.stdout.write(f"  [dry-run] orphan: {pi_id}")
            return

        finalized = 0
        quarantined = 0

        for pi_id in orphans:
            meta = self._pi_metadata(pi_id)
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
                    ct_payment_id=getattr(exc, "ct_payment_id", None)
                    or meta.get("ct_payment_id")
                    or "unknown",
                    ct_cart_id=getattr(exc, "ct_cart_id", None)
                    or meta.get("ct_cart_id")
                    or "unknown",
                    reason=str(exc),
                    source="recovery",
                )
                quarantined += 1
            except (CommercetoolsError, Exception) as exc:
                self.stderr.write(f"  [quarantine] {pi_id}: {exc}")
                _log_quarantine(
                    pi_id=pi_id,
                    ct_payment_id=meta.get("ct_payment_id") or "unknown",
                    ct_cart_id=meta.get("ct_cart_id") or "unknown",
                    reason=str(exc),
                    source="recovery",
                )
                quarantined += 1

        self.stdout.write(
            f"Recovery complete: {finalized} finalized, {quarantined} quarantined, "
            f"{len(orphans) - finalized - quarantined} skipped"
        )

    def _pi_metadata(self, pi_id: str) -> dict:
        try:
            pi = stripe.PaymentIntent.retrieve(pi_id)
            return dict(pi.metadata or {})
        except Exception:
            return {}

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

    def _discover_ct_orphans(
        self,
        created_after_iso: str,
        limit: int,
        already_found: set[str],
    ) -> list[str]:
        """
        CT secondary discovery: stripe_edx payments with a Success Charge and
        no linked Order. Returns Stripe PaymentIntent IDs (payment.interface_id).
        """
        orphan_ids = []
        offset = 0
        page_size = 50

        while len(orphan_ids) < limit:
            try:
                result = self.ct_api_client.base_client.payments.query(
                    where=[
                        f'paymentMethodInfo(paymentInterface="{EDX_STRIPE_PAYMENT_INTERFACE_NAME}")',
                        f'createdAt > "{created_after_iso}"',
                    ],
                    sort=["createdAt desc"],
                    limit=page_size,
                    offset=offset,
                )
            except CommercetoolsError:
                logger.warning(
                    "[recovery] CT payment query failed during secondary discovery",
                    exc_info=True,
                )
                break

            if not result.results:
                break

            for payment in result.results:
                if len(orphan_ids) >= limit:
                    break

                pi_id = payment.interface_id
                if not pi_id or pi_id in already_found or pi_id in orphan_ids:
                    continue

                if not self._payment_has_success_charge(payment):
                    continue

                try:
                    self.ct_api_client.get_order_by_payment_id(payment.id)
                    continue  # order exists
                except ValueError:
                    pass  # no order — candidate
                except CommercetoolsError:
                    logger.warning(
                        "[recovery] CT order lookup failed for payment %s",
                        payment.id,
                        exc_info=True,
                    )
                    continue

                if not self._stripe_pi_still_orphan(pi_id):
                    continue

                orphan_ids.append(pi_id)

            if len(result.results) < page_size:
                break
            offset += page_size

        if len(orphan_ids) >= limit:
            logger.info(
                "[recovery] CT secondary discovery truncated at limit=%d",
                limit,
            )

        return orphan_ids

    @staticmethod
    def _payment_has_success_charge(payment) -> bool:
        if not payment.transactions:
            return False
        return any(
            t.type == TransactionType.CHARGE and t.state == TransactionState.SUCCESS
            for t in payment.transactions
        )

    @staticmethod
    def _stripe_pi_still_orphan(pi_id: str) -> bool:
        """Confirm Stripe PI is succeeded commercetools and still missing order_id."""
        try:
            pi = stripe.PaymentIntent.retrieve(pi_id)
        except Exception:
            logger.warning(
                "[recovery] Failed to retrieve Stripe PI %s during CT secondary check",
                pi_id,
                exc_info=True,
            )
            return False

        if pi.status != "succeeded":
            return False

        metadata = pi.metadata or {}
        if metadata.get("source_system") != "commercetools":
            return False

        return not metadata.get("order_id")
