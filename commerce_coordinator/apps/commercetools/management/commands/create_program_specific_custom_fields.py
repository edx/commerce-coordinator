import json

from commercetools import CommercetoolsError
from commercetools.platform.models import TypeAddFieldDefinitionAction

from commerce_coordinator.apps.commercetools.catalog_info.foundational_types import TwoUCustomTypes
from commerce_coordinator.apps.commercetools.management.commands._ct_api_client_command import (
    CommercetoolsAPIClientCommand
)


class Command(CommercetoolsAPIClientCommand):
    help = 'Create custom fields for Program purchase'

    def handle_item_creation(self, custom_type):
        try:
            type_key = custom_type.key
            ret = self.ct_api_client.base_client.types.get_by_key(type_key)
            data = ret.serialize()
            print(f"{custom_type.resource_type_ids[0]} custom type with field {type_key} already exists: \n{
                json.dumps(data)}")

            existing_fields = [field.get('name') for field in data.get('fieldDefinitions', [])]

            for field in custom_type.field_definitions:
                if field.name not in existing_fields:
                    update_action = TypeAddFieldDefinitionAction(field_definition=field)
                    ret = self.ct_api_client.base_client.types.update_by_id(
                        data.get('id'), data.get('version'), actions=[update_action]
                    )

        except CommercetoolsError as ex:
            ret = self.ct_api_client.base_client.types.create(custom_type)
            print(f"Created {custom_type.resource_type_ids[0]} custom type with field {type_key}: {
                json.dumps(ret.serialize())}")

    def handle(self, *args, **options):
        self.handle_item_creation(TwoUCustomTypes.PROGRAM_LINE_ITEM_TYPE_DRAFT)
        self.handle_item_creation(TwoUCustomTypes.RETURN_ITEM_TYPE_DRAFT)
