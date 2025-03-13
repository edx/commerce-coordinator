import sys
import json

from typing import Literal, Union

from commercetools import CommercetoolsError
from commercetools.platform.models import TypeAddFieldDefinitionAction, TypeChangeNameAction


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


def handle_custom_item_creation(ct_api_client, custom_type):
    try:
        type_key = custom_type.key
        ret = ct_api_client.base_client.types.get_by_key(type_key)
        data = ret.serialize()
        print(f"{custom_type.resource_type_ids[0]} custom type with field {type_key} already exists: \n{
            json.dumps(data)}")

        existing_fields = [field.get('name') for field in data.get('fieldDefinitions', [])]
        update_actions = []
        if data.get('name')['en'] != custom_type.name['en']:
            update_actions.append(TypeChangeNameAction(name=custom_type.name))

        for field in custom_type.field_definitions:
            if field.name not in existing_fields:
                update_actions.append(TypeAddFieldDefinitionAction(field_definition=field))
                print(f"Creating field: {field.name} for custom type: {type_key}")
        
        if update_actions:
            ret = ct_api_client.base_client.types.update_by_id(
                data.get('id'), data.get('version'), actions=update_actions
            )
            print(f"Updated fields for custom type: {type_key} {json.dumps(ret.serialize())}")
        else:
            print(f"No update required for custom type: {type_key}")

    except CommercetoolsError as ex:
        ret = ct_api_client.base_client.types.create(custom_type)
        print(f"Created {custom_type.resource_type_ids[0]} custom type with field {type_key}: {
            json.dumps(ret.serialize())}")
