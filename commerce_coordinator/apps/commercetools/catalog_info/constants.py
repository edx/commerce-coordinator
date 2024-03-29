class TwoUKeys:
    """Global 2U Object Keys for use in Commercetools"""
    CROSS_SYS_USER_INFO_TYPE = '2u-user_information'

    SDN_SANCTIONED_ORDER_STATE = '2u-sdn-order-state'


class EdXFieldNames:
    """edX Specific field names for use in Commercetools"""
    LMS_USER_ID = 'edx-lms_user_id'
    LMS_USER_NAME = 'edx-lms_user_name'


class Languages:
    """Language codes using IETF language tag format, as described in BCP 47."""
    ENGLISH = 'en'
    US_ENGLISH = 'en-US'


LS_OUT_PREFERENCES = [Languages.ENGLISH, Languages.US_ENGLISH]
"""Default preferred output languages if one isnt provided from LocalizedString dictionaries"""

HIDE_CODE_FOR_CURRENCIES = ['USD', 'EUR', 'INR', 'JPY']
"""Currencies to hide the code on, so $12 isn't $12 USD."""

SEND_MONEY_AS_DECIMAL_STRING = True
"""Sends money values as decimal numbers only ('$123.99 AUD' becomes '123.99' when True)"""

DEFAULT_ORDER_EXPANSION = (
    "state",
    "paymentInfo.payments[*]",
    "discountCodes[*].discountCode",
    "directDiscounts[*]"
)

STRIPE_PAYMENT_STATUS_INTERFACE_CODE_SUCCEEDED = "succeeded"

EDX_STRIPE_PAYMENT_INTERFACE_NAME = "stripe_edx"
