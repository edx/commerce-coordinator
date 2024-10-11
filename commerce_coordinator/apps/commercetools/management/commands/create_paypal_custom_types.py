import json

from commercetools import CommercetoolsError

from commerce_coordinator.apps.commercetools.catalog_info.foundational_types import TwoUCustomTypes, TwoUCustomObjects
from commerce_coordinator.apps.commercetools.management.commands._ct_api_client_command import (
    CommercetoolsAPIClientCommand
)


class Command(CommercetoolsAPIClientCommand):
    help = "Create the Payment Custom Type/Fields for PayPal"

    def handle(self, *args, **options):
        current_draft = TwoUCustomTypes.PAYMENT_TYPE_DRAFT
        type_key = current_draft.key
        custom_object_draft = TwoUCustomObjects.PAYPAL_CUSTOM_OBJECT_DRAFT

        try:
            custom_object = self.ct_api_client.base_client.custom_objects.create_or_update(draft=custom_object_draft)
            print(f"PayPal custom object already exists: {json.dumps(custom_object.serialize())}")
        except CommercetoolsError as ex:
            print(f"Error in creating/updating PayPal custom object: {str(ex)}")


        try:
            ret = self.ct_api_client.base_client.types.get_by_key(type_key)
            print(f"Payment custom type already exists: {json.dumps(ret.serialize())}")
        except CommercetoolsError as _:
            ret = self.ct_api_client.base_client.types.create(
                TwoUCustomTypes.PAYMENT_TYPE_DRAFT
            )
            print(f"Created new Payment custom type: {json.dumps(ret.serialize())}")
