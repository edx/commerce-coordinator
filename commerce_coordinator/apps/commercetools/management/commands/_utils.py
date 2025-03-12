import sys
import json

from typing import Literal, Union

from commercetools import CommercetoolsError
from commercetools.platform.models import TypeAddFieldDefinitionAction


def yn(question: str, default: Union[Literal['y', 'n']] = "n"):
    y = "Y" if default == "y" else "y"
    n = "N" if default == "n" else "n"

    opts = f"[{y}/{n}]"

    resps = {"yes": True, "no": False, "y": True, "n": False}
    while True:
        sys.stdout.write(f"{question} {opts}? ")
        choice = input().strip().lower()

        if default is not None and len(choice) == 0:
            return default
        elif choice in resps.keys():
            return resps[choice]
        else:
            sys.stdout.write("Please choose y or n.\n")


def handle_custom_item_creation(self, custom_type):
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
                print(f"Created field: {field.name} for custom type: {type_key} {json.dumps(ret.serialize())}")

    except CommercetoolsError as ex:
        ret = self.ct_api_client.base_client.types.create(custom_type)
        print(f"Created {custom_type.resource_type_ids[0]} custom type with field {type_key}: {
            json.dumps(ret.serialize())}")
