from commercetools.platform.models import (
    CustomFieldBooleanType,
    CustomFieldEnumType,
    CustomFieldNumberType,
    CustomFieldStringType,
    CustomObjectDraft,
    FieldDefinition,
    ResourceTypeId,
    StateDraft,
    StateResourceIdentifier,
    StateTypeEnum,
    TypeDraft,
    TypeTextInputHint
)

from commerce_coordinator.apps.commercetools.catalog_info.constants import (
    CART_DISCOUNT_CATEGORIES,
    CART_DISCOUNT_CHANNELS,
    CART_DISCOUNT_TYPES,
    EdXFieldNames,
    TwoUKeys
)
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

    # 2U Cross System User Information for Customer Objects
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

    RETURN_ITEM_TYPE_DRAFT = TypeDraft(
       key=TwoUKeys.RETURN_ITEM_CUSTOM_TYPE,
       name=ls({'en': 'Return Item Custom Type'}),
       resource_type_ids=[ResourceTypeId.ORDER_RETURN_ITEM],
       # ^^^ this cannot be updated, the whole type has to be unassigned, removed and replaced.
       field_definitions=[
            # Updating Field Definitions only supports:
            # - basic field definitions changes, like label and input_hint, not type or
            # - whether it is required or not.
            # - It can add new ones.
            # If you need something done that can't be, the whole type has to be unassigned, removed and replaced.

            FieldDefinition(
                type=CustomFieldStringType(),
                name=TwoUKeys.TRANSACTION_ID,
                required=False,
                label=ls({'en': 'Transaction ID'}),
                input_hint=TypeTextInputHint.SINGLE_LINE
            ),
            FieldDefinition(
                type=CustomFieldStringType(),
                name=TwoUKeys.LINE_ITEM_LMS_ENTITLEMENT_ID,
                required=False,
                label=ls({'en': 'edX LMS Entitlement ID'}),
                input_hint=TypeTextInputHint.SINGLE_LINE
            )
       ]
    )

    TRANSACTION_TYPE_DRAFT = TypeDraft(
        key=TwoUKeys.TRANSACTION_CUSTOM_TYPE,
        name=ls({'en': 'Transaction Custom Type'}),
        resource_type_ids=[ResourceTypeId.TRANSACTION],
        # ^^^ this cannot be updated, the whole type has to be unassigned, removed and replaced.
        field_definitions=[
            # Updating Field Definitions only supports:
            # - basic field definitions changes, like label and input_hint, not type or
            # - whether it is required or not.
            # - It can add new ones.
            # If you need something done that can't be, the whole type has to be unassigned, removed and replaced.

            FieldDefinition(
                type=CustomFieldStringType(),
                name=TwoUKeys.RETURN_ITEM_ID,
                required=False,
                label=ls({'en': 'Return Item ID'}),
                input_hint=TypeTextInputHint.SINGLE_LINE
            ),
            FieldDefinition(
                type=CustomFieldNumberType(),
                name=TwoUKeys.TRANSACTION_USD_CENT_AMOUNT,
                required=False,
                label=ls({'en': 'USD Cent Amount'}),
                input_hint=TypeTextInputHint.SINGLE_LINE
            )
        ]
    )

    LINE_ITEMS_BUNDLE_TYPE_DRAFT = TypeDraft(
        key=TwoUKeys.LINE_ITEM_BUNDLE_CUSTOM_TYPE,
        name=ls({'en': "Line Item's Bundle Custom Type"}),
        resource_type_ids=[ResourceTypeId.LINE_ITEM],

        field_definitions=[
            FieldDefinition(
                type=CustomFieldStringType(),
                name=TwoUKeys.LINE_ITEM_BUNDLE_ID,
                required=False,
                label=ls({'en': 'Bundle ID'}),
                input_hint=TypeTextInputHint.SINGLE_LINE
            ),
            FieldDefinition(
                type=CustomFieldStringType(),
                name=TwoUKeys.LINE_ITEM_LMS_ENTITLEMENT_ID,
                required=False,
                label=ls({'en': 'edX LMS Entitlement ID'}),
                input_hint=TypeTextInputHint.SINGLE_LINE
            )
        ]
    )

    CART_DISCOUNT_TYPE_DRAFT = TypeDraft(
        key=TwoUKeys.CART_DISCOUNT_CUSTOM_TYPE,
        name=ls({'en': "Cart Discount Custom Type"}),
        resource_type_ids=[ResourceTypeId.CART_DISCOUNT],

        field_definitions=[
            FieldDefinition(
                type=CustomFieldStringType(),
                name=TwoUKeys.CART_DISCOUNT_CLIENT,
                required=False,
                label=ls({'en': 'Client'}),
                input_hint=TypeTextInputHint.SINGLE_LINE
            ),
            FieldDefinition(
                type=CustomFieldEnumType(values=CART_DISCOUNT_CATEGORIES),
                name=TwoUKeys.CART_DISCOUNT_CATEGORY,
                required=False,
                label=ls({'en': 'Category'}),
                input_hint=TypeTextInputHint.SINGLE_LINE,
            ),
            FieldDefinition(
                type=CustomFieldEnumType(values=CART_DISCOUNT_TYPES),
                name=TwoUKeys.CART_DISCOUNT_DISCOUNT_TYPE,
                required=False,
                label=ls({'en': 'Discount Type'}),
                input_hint=TypeTextInputHint.SINGLE_LINE
            ),
            FieldDefinition(
                type=CustomFieldEnumType(values=CART_DISCOUNT_CHANNELS),
                name=TwoUKeys.CART_DISCOUNT_CHANNEL,
                required=False,
                label=ls({'en': 'Channel'}),
                input_hint=TypeTextInputHint.SINGLE_LINE,
            ),
        ]
    )

    # It would be same for cart and order
    ORDER_TYPE_DRAFT = TypeDraft(
        key=TwoUKeys.ORDER_CUSTOM_TYPE,
        name=ls({'en': "Order Custom Type"}),
        resource_type_ids=[ResourceTypeId.ORDER],

        field_definitions=[
            FieldDefinition(
                type=CustomFieldStringType(),
                name=TwoUKeys.ORDER_ORDER_NUMBER,
                required=False,
                label=ls({'en': 'Human Readable Order Number'}),
                input_hint=TypeTextInputHint.SINGLE_LINE
            ),
            FieldDefinition(
                type=CustomFieldStringType(),
                name=TwoUKeys.ORDER_EMAIL_DOMAIN,
                required=False,
                label=ls({'en': 'Email Domain'}),
                input_hint=TypeTextInputHint.SINGLE_LINE
            ),
            FieldDefinition(
                type=CustomFieldBooleanType(),
                name=TwoUKeys.ORDER_MOBILE_ORDER,
                required=False,
                label=ls({'en': 'Mobile Order'}),
                input_hint=TypeTextInputHint.SINGLE_LINE
            )
        ]
    )


class TwoUCustomObjects:
    PAYPAL_CUSTOM_OBJECT_DRAFT = CustomObjectDraft(
        container=TwoUKeys.PAYPAL_CONNECTOR_CONTAINER,
        key=TwoUKeys.PAYPAL_CONNECTOR_SETTINGS_KEY,
        value={
            "merchantId": "",  # string
            "email": "test@example.com",  # string
            "acceptPayPal": True,  # boolean
            "acceptPayLater": False,  # boolean
            "acceptVenmo": False,  # boolean
            "acceptLocal": False,  # boolean
            "acceptCredit": False,  # boolean
            "buttonPaymentPage": False,  # boolean
            "buttonCartPage": False,  # boolean
            "buttonDetailPage": False,  # boolean
            "buttonShippingPage": False,  # boolean
            "buttonShape": "pill",  # "rect" | "pill"
            "buttonTagline": False,  # boolean
            "payLaterMessagingType": {},  # Record<string, "flex" | "text">
            "payLaterMessageHomePage": False,  # boolean
            "payLaterMessageCategoryPage": False,  # boolean
            "payLaterMessageDetailsPage": False,  # boolean
            "payLaterMessageCartPage": False,  # boolean
            "payLaterMessagePaymentPage": False,  # boolean
            "payLaterMessageTextLogoType": "none",  # "inline" | "primary" | "alternative" | "none"
            "payLaterMessageTextLogoPosition": "left",  # "left" | "right" | "top"
            "payLaterMessageTextColor": "black",  # "black" | "white" | "monochrome" | "grayscale"
            "payLaterMessageTextSize": "10",  # "10" | "11" | "12" | "13" | "14" | "15" | "16"
            "payLaterMessageTextAlign": "left",  # "left" | "center" | "right"
            # "blue" | "black" | "white" | "white-no-border" | "gray" | "monochrome" | "grayscale"
            "payLaterMessageFlexColor": "blue",
            "payLaterMessageFlexRatio": "1x1",  # "1x1" | "1x4" | "8x1" | "20x1"
            "threeDSOption": "",  # "" | "SCA_ALWAYS" | "SCA_WHEN_REQUIRED"
            "payPalIntent": "Capture",  # "Authorize" | "Capture"
            "ratePayBrandName": {},  # CustomDataStringObject
            "ratePayLogoUrl": {},  # CustomDataStringObject
            "ratePayCustomerServiceInstructions": {},  # CustomDataStringObject
            "paymentDescription": {},  # CustomDataStringObject
            "storeInVaultOnSuccess": False,  # boolean
            "paypalButtonConfig": {  # PayPal button configuration
                "buttonColor": "blue",  # "gold" | "blue" | "white" | "silver" | "black"
                "buttonLabel": "buynow",  # "paypal" | "checkout" | "buynow" | "pay" | "installment"
            },
            "hostedFieldsPayButtonClasses": "",  # string
            "hostedFieldsInputFieldClasses": "",  # string
            "threeDSAction": {},  # Record<string, any>
        }

    )
