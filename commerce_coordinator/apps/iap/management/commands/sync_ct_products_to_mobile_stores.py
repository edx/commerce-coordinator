"""
This command fetches new course runs for mobile supported courses and creates seats/SKUS for them using CommerceTools.
"""
import logging

from datetime import datetime, timezone
import uuid

from django.core.management import BaseCommand

from commerce_coordinator.apps.commercetools.catalog_info.edx_utils import cents_to_dollars
from commerce_coordinator.apps.commercetools.catalog_info.utils import attribute_dict
from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient
from commerce_coordinator.apps.commercetools.catalog_info.constants import EdXFieldNames
from commerce_coordinator.apps.core.models import User
from commerce_coordinator.apps.iap.utils import create_ios_product, get_standalone_price_for_sku

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    Create Seats/SKUs for new course runs of courses that have mobile payments enabled.
    """

    def handle(self, *args, **options):
        """
        Create Seats/SKUs for new course runs of courses that have mobile payments enabled.
        """
        ct_client = CommercetoolsAPIClient()

        # Get all products from CommerceTools that need mobile SKUs
        product_variants_to_sync = self._get_product_variants_to_sync_to_mobile_stores(ct_client)

        if not product_variants_to_sync:
            logger.info("No product variants to sync to mobile stores")
            return

        variants_to_sync = []
        for product_variant in product_variants_to_sync:
            for variant in product_variant.variants:
                price = cents_to_dollars(variant.price.value) if variant.price else None

                attributes_dict = attribute_dict(variant.attributes)
                course_mode = attributes_dict.get('course-mode')
                course_run_end = attributes_dict.get('courserun-end')
                verification_upgrade_deadline = attributes_dict.get('verification-upgrade-deadline')

                if(
                    price and price < 1000 and course_mode == 'verified' and
                    verification_upgrade_deadline > datetime.now(timezone.utc).isoformat() and
                    course_run_end > datetime.now(timezone.utc).strftime('%Y-%m-%d')
                ):
                    uuid_str = attributes_dict.get('courserun-uuid')
                    course_run_uuid = str(uuid.UUID(uuid_str)) if uuid_str else None

                    variants_to_sync.append({
                        'price': price,
                        'name': product_variant.name,
                        'key': course_run_uuid,
                    })
                    create_ios_product(product_variant, course_run_uuid, configuration)

    def _get_product_variants_to_sync_to_mobile_stores(
        self, ct_client: CommercetoolsAPIClient
    ) -> list:
        """Get the parent product that needs mobile SKUs created."""
        return ct_client.get_product_variants_with_price(
            where=[
                'variants(attributes(value="verified"))',
                f'variants(attributes(name="verification-upgrade-deadline" and value>="{datetime.now(timezone.utc).isoformat()}"))'
            ]
        )
