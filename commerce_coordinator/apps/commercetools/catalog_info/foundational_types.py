from commercetools.platform.models import (
    CustomFieldStringType,
    FieldDefinition,
    ResourceTypeId,
    TypeDraft,
    TypeTextInputHint
)

from commerce_coordinator.apps.commercetools.catalog_info.constants import EdXFieldNames, TwoUKeys
from commerce_coordinator.apps.commercetools.catalog_info.utils import ls


class TwoUCustomTypes:
    """Global 2U Custom Type Definitions in Commercetools"""
    CUSTOMER_TYPE_DRAFT = TypeDraft(
        key=TwoUKeys.CROSS_SYS_USER_INFO_TYPE,
        name=ls({'en': '2U Cross System User Information'}),
        resource_type_ids=[ResourceTypeId.CUSTOMER],
        description=ls({'en': '2U Cross System User Information, shared among all LOBs and '
                              'by various LMS and backend systems.'}),
        # ^^^ this cannot be updated, the whole type has to be unassigned, removed and replaced.
        field_definitions=[

            # Updating Field Definitions only supports:
            # - basic field definitions changes, like label and input_hint, not type or
            # - whether it is required or not.
            # - It can add new ones.
            # If you need something done that can't be, the whole type has to be unassigned, removed and replaced.

            FieldDefinition(
                type=CustomFieldStringType(),
                name=EdXFieldNames.LMS_USER_ID,
                required=False,
                label=ls({'en': 'edX LMS User Identifier'}),
                input_hint=TypeTextInputHint.SINGLE_LINE
            ),
            FieldDefinition(
                type=CustomFieldStringType(),
                name=EdXFieldNames.LMS_USER_NAME,
                required=False,
                label=ls({'en': 'edX LMS User Name'}),
                input_hint=TypeTextInputHint.SINGLE_LINE
            )
        ]
    )
