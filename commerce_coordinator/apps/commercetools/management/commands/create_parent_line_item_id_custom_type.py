import json

from commercetools import CommercetoolsError

from commerce_coordinator.apps.commercetools.catalog_info.foundational_types import TwoUCustomTypes
from commerce_coordinator.apps.commercetools.management.commands._ct_api_client_command import (
    CommercetoolsAPIClientCommand
)


class Command(CommercetoolsAPIClientCommand):
    help = 'Create a custom type for parentLineItemId'

    def handle(self, *args, **options):
        current_draft = TwoUCustomTypes.PARENT_LINE_ITEM_ID_TYPE_DRAFT
        type_key = current_draft.key

        # self.ct_api_client.base_client.types.delete_by_id('3a4e8a3e-aea4-4c9c-8e10-828059ecdad0', 1)

        try:
            ret = self.ct_api_client.base_client.types.get_by_key(type_key)
            print(f"LineItem custom type with field parentLineItemId already exists: {json.dumps(ret.serialize())}")
        except CommercetoolsError as ex:
            ret = self.ct_api_client.base_client.types.create(
                TwoUCustomTypes.PARENT_LINE_ITEM_ID_TYPE_DRAFT
            )
            print(f"Created ReturnItem custom type with field transactionId: {json.dumps(ret.serialize())}")
