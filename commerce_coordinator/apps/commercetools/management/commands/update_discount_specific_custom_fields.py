from commerce_coordinator.apps.commercetools.catalog_info.foundational_types import TwoUCustomTypes
from commerce_coordinator.apps.commercetools.management.commands._ct_api_client_command import (
    CommercetoolsAPIClientCommand
)
from commerce_coordinator.apps.commercetools.management.commands._utils import handle_custom_field_enums_update


class Command(CommercetoolsAPIClientCommand):
    help = 'Update custom fields for Discounts'

    def handle(self, *args, **options):
        handle_custom_field_enums_update(self.ct_api_client, TwoUCustomTypes.CART_DISCOUNT_TYPE_DRAFT)
