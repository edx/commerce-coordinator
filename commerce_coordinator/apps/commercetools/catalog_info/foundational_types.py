from commercetools.platform.models import (
    CustomFieldNumberType,
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
        field_definitions=[
            FieldDefinition(
                type=CustomFieldNumberType(),
                name=EdXFieldNames.LMS_USER_ID,
                required=False,
                label=ls({'en': 'edX LMS User Identifier'}),
                input_hint=TypeTextInputHint.SINGLE_LINE
            )
        ]
    )
