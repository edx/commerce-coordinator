import json
import sys
from typing import Literal, Union

from commercetools import CommercetoolsError
from commercetools.platform.models import TypeAddEnumValueAction, TypeAddFieldDefinitionAction, TypeChangeNameAction


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


def handle_custom_field_creation(ct_api_client, custom_type):
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
            print(f"Updatig custom type name from '{data.get('name')['en']}' to '{custom_type.name['en']}'")

        for field in custom_type.field_definitions:
            if field.name not in existing_fields:
                update_actions.append(TypeAddFieldDefinitionAction(field_definition=field))
                print(f"Creating field: {field.name} for custom type: {type_key}")

        if update_actions:
            ret = ct_api_client.base_client.types.update_by_id(
                data.get('id'), data.get('version'), actions=update_actions
            )
            print(f"Updated custom type: {type_key} {json.dumps(ret.serialize())}")
        else:
            print(f"No update required for custom type: {type_key}")

    except CommercetoolsError as ex:
        ret = ct_api_client.base_client.types.create(custom_type)
        print(f"Created {custom_type.resource_type_ids[0]} custom type with field {type_key}: {
            json.dumps(ret.serialize())}")


def handle_custom_field_enums_update(ct_api_client, custom_type):
    try:
        type_key = custom_type.key
        ret = ct_api_client.base_client.types.get_by_key(type_key)
        data = ret.serialize()

        CUSTOM_FIELD_ENUM_NAME = 'Enum'
        existing_enum_fields = {field.get('name'): field.get('type').get('values', [])
                                for field in data.get('fieldDefinitions', [])
                                if field.get('type').get('name') == CUSTOM_FIELD_ENUM_NAME}
        update_actions = []

        for field in custom_type.field_definitions:
            if field.type.name == CUSTOM_FIELD_ENUM_NAME:
                existing_enum_keys = [existing_enum.get('key') for existing_enum
                                      in existing_enum_fields.get(field.name, [])]
                for field_enum in field.type.values:
                    if field_enum.get('key') not in existing_enum_keys:
                        update_actions.append(TypeAddEnumValueAction(field_name=field.name, value=field_enum))
                        print(f"Creating enum value: {field_enum.get('key')} for field: {
                            field.name} in custom type: {type_key}")

                    else:
                        print(f'Enum values {field_enum.get('label')} already exist custom type: {field.name}')

        if update_actions:
            ret = ct_api_client.base_client.types.update_by_id(
                data.get('id'), data.get('version'), actions=update_actions
            )
            print(f"Updated custom type: {type_key} {json.dumps(ret.serialize())}")
        else:
            print(f"No update required for custom type: {type_key}")

    except CommercetoolsError:
        handle_custom_field_creation(ct_api_client, custom_type)
