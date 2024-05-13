from commercetools.platform.models import (
    CustomFieldStringType,
    FieldDefinition,
    ResourceTypeId,
    StateDraft,
    StateResourceIdentifier,
    StateTypeEnum,
    TypeDraft,
    TypeTextInputHint
)

from commerce_coordinator.apps.commercetools.catalog_info.constants import EdXFieldNames, TwoUKeys
from commerce_coordinator.apps.commercetools.catalog_info.utils import ls


class TwoUCustomStates:
    """Global 2U Workflow Transition State Definitions in Commercetools"""

    # Order States
    SANCTIONED_ORDER_STATE = StateDraft(
        key=TwoUKeys.SDN_SANCTIONED_ORDER_STATE,
        type=StateTypeEnum.ORDER_STATE,
        name=ls({'en': 'Sanctioned'}),
        description=ls({'en': 'This order has been sanctioned for an SDN hit'}),
        transitions=None
    )

    # Line Item States
    INITIAL_FULFILLMENT_STATE = StateDraft(
        key=TwoUKeys.INITIAL_FULFILMENT_STATE,
        type=StateTypeEnum.LINE_ITEM_STATE,
        name=ls({'en': 'Fulfillment Initial'}),
        description=ls({'en': 'This order line item has not yet been fulfilled'}),
        initial=True,
        transitions=[
            StateResourceIdentifier(key=TwoUKeys.PENDING_FULFILMENT_STATE)
        ]
    )

    PENDING_FULFILLMENT_STATE = StateDraft(
        key=TwoUKeys.PENDING_FULFILMENT_STATE,
        type=StateTypeEnum.LINE_ITEM_STATE,
        name=ls({'en': 'Fulfillment Pending'}),
        description=ls({'en': 'This order line item is pending fulfilment'}),
        initial=False,
        transitions=[
            StateResourceIdentifier(key=TwoUKeys.PROCESSING_FULFILMENT_STATE)
        ]
    )

    PROCESSING_FULFILLMENT_STATE = StateDraft(
        key=TwoUKeys.PROCESSING_FULFILMENT_STATE,
        type=StateTypeEnum.LINE_ITEM_STATE,
        name=ls({'en': 'Fulfillment Processing'}),
        description=ls({'en': 'This order line item is processing fulfilment'}),
        initial=False,
        transitions=[
            StateResourceIdentifier(key=TwoUKeys.SUCCESS_FULFILMENT_STATE),
            StateResourceIdentifier(key=TwoUKeys.FAILURE_FULFILMENT_STATE)
        ]
    )

    SUCCESS_FULFILLMENT_STATE = StateDraft(
        key=TwoUKeys.SUCCESS_FULFILMENT_STATE,
        type=StateTypeEnum.LINE_ITEM_STATE,
        name=ls({'en': 'Fulfillment Success'}),
        description=ls({'en': 'This order line item has successfully been fulfilled'}),
        initial=False,
        transitions=[]
    )

    FAILED_FULFILLMENT_STATE = StateDraft(
        key=TwoUKeys.FAILURE_FULFILMENT_STATE,
        type=StateTypeEnum.LINE_ITEM_STATE,
        name=ls({'en': 'Fulfillment Failure'}),
        description=ls({'en': 'This order line item was unsuccessfully fulfilled'}),
        initial=False,
        transitions=[
            StateResourceIdentifier(key=TwoUKeys.PENDING_FULFILMENT_STATE),
            StateResourceIdentifier(key=TwoUKeys.SUCCESS_FULFILMENT_STATE)
        ]
    )


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
    """2U Cross System User Information for Customer Objects"""
