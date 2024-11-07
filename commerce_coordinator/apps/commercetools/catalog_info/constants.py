class TwoUKeys:
    """Global 2U Object Keys for use in Commercetools"""

    # 2U Custom Types
    # Customer Custom Fields Types
    CROSS_SYS_USER_INFO_TYPE = '2u-user_information'

    # Order States
    SDN_SANCTIONED_ORDER_STATE = '2u-sdn-order-state'

    # Line Item Fulfillment States
    INITIAL_FULFILMENT_STATE = 'Initial'  # this key doesn't match our format because it is built in.
    PENDING_FULFILMENT_STATE = '2u-fulfillment-pending-state'
    PROCESSING_FULFILMENT_STATE = '2u-fulfillment-processing-state'
    SUCCESS_FULFILMENT_STATE = '2u-fulfillment-success-state'
    FAILURE_FULFILMENT_STATE = '2u-fulfillment-failure-state'

    # Payment Custom Type Keys for PayPal
    PAYPAL_PAYMENT_TYPE = 'paypal-payment-type'

    # Payment Custom Fields Keys for PayPal
    PAYPAL_ORDER_ID_FIELD_KEY = 'PayPalOrderId'
    PAYPAL_CLIENT_TOKEN_REQUEST_FIELD_KEY = 'getClientTokenRequest'
    PAYPAL_CLIENT_TOKEN_RESPONSE_FIELD_KEY = 'getClientTokenResponse'
    PAYPAL_CREATE_ORDER_REQUEST_FIELD_KEY = 'createPayPalOrderRequest'
    PAYPAL_CREATE_ORDER_RESPONSE_FIELD_KEY = 'createPayPalOrderResponse'
    PAYPAL_CAPTURE_ORDER_REQUEST_FIELD_KEY = 'capturePayPalOrderRequest'
    PAYPAL_CAPTURE_ORDER_RESPONSE_FIELD_KEY = 'capturePayPalOrderResponse'
    PAYPAL_UPDATE_ORDER_REQUEST_FIELD_KEY = 'updatePayPalOrderRequest'
    PAYPAL_UPDATE_ORDER_RESPONSE_FIELD_KEY = 'updatePayPalOrderResponse'

    # Custom Objects keys
    PAYPAL_CONNECTOR_CONTAINER = 'paypal-commercetools-connector'
    PAYPAL_CONNECTOR_SETTINGS_KEY = 'settings'

    # Return Item Types
    RETURN_ITEM_CUSTOM_TYPE = 'returnItemCustomType'

    # Return Item Custom Fields
    TRANSACTION_ID = 'transactionId'

    # Transaction Types
    TRANSACTION_CUSTOM_TYPE = 'transactionCustomType'

    # Transaction Custom Fields
    RETURN_ITEM_ID = 'returnItemId'


class EdXFieldNames:
    """edX Specific field names for use in Commercetools"""

    # 2U Custom Types
    # Customer Custom Fields Types
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
    'lineItems[*].productType.obj',
    "paymentInfo.payments[*]",
    "discountCodes[*].discountCode",
    "directDiscounts[*]"
)

STRIPE_PAYMENT_STATUS_INTERFACE_CODE_SUCCEEDED = "succeeded"
PAYPAL_PAYMENT_STATUS_INTERFACE_CODE_SUCCEEDED = "COMPLETED"

EDX_STRIPE_PAYMENT_INTERFACE_NAME = "stripe_edx"
EDX_PAYPAL_PAYMENT_INTERFACE_NAME = "paypal_edx"
