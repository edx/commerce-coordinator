import json
import pprint
from typing import List

from commercetools import CommercetoolsError
from commercetools.platform.models import (
    FieldDefinition,
    TypeAddFieldDefinitionAction,
    TypeChangeFieldDefinitionLabelAction,
    TypeChangeInputHintAction,
    TypeChangeLabelAction,
    TypeChangeNameAction,
    TypeSetDescriptionAction,
    TypeUpdateAction
)
from django.core.management.base import no_translations

from commerce_coordinator.apps.commercetools.catalog_info.foundational_types import TwoUCustomTypes
from commerce_coordinator.apps.commercetools.catalog_info.utils import ls_eq
from commerce_coordinator.apps.commercetools.management.commands._ct_api_client_command import (
    CommercetoolsAPIClientCommand
)
from commerce_coordinator.apps.commercetools.management.commands._utils import yn


class Command(CommercetoolsAPIClientCommand):
    help = "Insert or Update the base 2U Customer Custom Type Object"

    # Django Overrides

    @no_translations
    def handle(self, *args, **options):
        current_draft = TwoUCustomTypes.CUSTOMER_TYPE_DRAFT
        type_key = current_draft.key
        try:
            ret = self.ct_api_client.base_client.types.get_by_key(type_key)
        except CommercetoolsError as _:
            ret = self.ct_api_client.base_client.types.create(
                TwoUCustomTypes.CUSTOMER_TYPE_DRAFT
            )
            print(json.dumps(ret.serialize()))
            exit()

        actions: list[TypeUpdateAction] = []

        if not ls_eq(current_draft.name, ret.name):
            actions.append(TypeChangeNameAction(name=current_draft.name))
        if not ls_eq(current_draft.description, ret.description):
            actions.append(TypeSetDescriptionAction(description=current_draft.description))

        ret_field_def_names = [fd.name for fd in ret.field_definitions]

        for draft_def in current_draft.field_definitions:
            if draft_def.name in ret_field_def_names:  # we have a field by this name online already
                ret_field_def: FieldDefinition = list(
                    filter(lambda fd: fd.name == draft_def.name, ret.field_definitions)
                )[-1]

                if not ls_eq(ret_field_def.label, draft_def.label):
                    actions.append(
                        TypeChangeFieldDefinitionLabelAction(field_name=draft_def.name, label=draft_def.label)
                    )
                if ret_field_def.input_hint != draft_def.input_hint:
                    actions.append(
                        TypeChangeInputHintAction(field_name=draft_def.name, input_hint=draft_def.input_hint)
                    )
            else:  # its missing we need to add it
                actions.append(TypeAddFieldDefinitionAction(field_definition=draft_def))

        pprint.pprint(actions)

        if not yn("Are the actions above what you expect to be changed"):
            print("Script terminated by user.")
            exit(0)

        print("Submitting the following actions: " + json.dumps([x.serialize() for x in actions]))

        ret = self.ct_api_client.base_client.types.update_by_key(
            type_key,
            ret.version,
            actions=actions
        )

        print(json.dumps(ret.serialize()))
