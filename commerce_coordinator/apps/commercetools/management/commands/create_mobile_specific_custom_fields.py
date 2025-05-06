from commerce_coordinator.apps.commercetools.catalog_info.foundational_types import TwoUCustomTypes
from commerce_coordinator.apps.commercetools.management.commands._ct_api_client_command import (
    CommercetoolsAPIClientCommand
)
from commerce_coordinator.apps.commercetools.management.commands._utils import handle_custom_field_creation


class Command(CommercetoolsAPIClientCommand):
    help = 'Create custom fields for mobile APIs'

    def handle(self, *args, **options):
        handle_custom_field_creation(self.ct_api_client, TwoUCustomTypes.TRANSACTION_TYPE_DRAFT)
        handle_custom_field_creation(self.ct_api_client, TwoUCustomTypes.ORDER_TYPE_DRAFT)
