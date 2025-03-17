from commerce_coordinator.apps.commercetools.catalog_info.foundational_types import TwoUCustomTypes
from commerce_coordinator.apps.commercetools.management.commands._ct_api_client_command import (
    CommercetoolsAPIClientCommand
)
from commerce_coordinator.apps.commercetools.management.commands._utils import handle_custom_field_creation


class Command(CommercetoolsAPIClientCommand):
    help = 'Create custom fields for Bundle purchase'

    def handle(self, *args, **options):
        handle_custom_field_creation(TwoUCustomTypes.LINE_ITEMS_BUNDLE_TYPE_DRAFT)
        handle_custom_field_creation(TwoUCustomTypes.RETURN_ITEM_TYPE_DRAFT)
