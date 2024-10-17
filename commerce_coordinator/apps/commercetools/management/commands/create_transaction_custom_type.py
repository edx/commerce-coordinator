import json

from commercetools import CommercetoolsError
from commerce_coordinator.apps.commercetools.catalog_info.foundational_types import TwoUCustomTypes
from commerce_coordinator.apps.commercetools.management.commands._ct_api_client_command import (
    CommercetoolsAPIClientCommand
)


class Command(CommercetoolsAPIClientCommand):
    help = 'Create a custom type for transactions with field returnItemId'

    def handle(self, *args, **options):
        current_draft = TwoUCustomTypes.TRANSACTION_TYPE_DRAFT
        type_key = current_draft.key

        try:
            ret = self.ct_api_client.base_client.types.get_by_key(type_key)
            print(f"Transaction custom type with field returnItemId already exists: {json.dumps(ret.serialize())}")
        except CommercetoolsError as ex:
            ret = self.ct_api_client.base_client.types.create(
                TwoUCustomTypes.TRANSACTION_TYPE_DRAFT
            )
            print(f"Created Transaction custom type with field returnItemId: {json.dumps(ret.serialize())}")
