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
    # USD Amount field to store in Transaction model
    TRANSACTION_USD_CENT_AMOUNT = 'usdCentAmount'

    # Bundle specifiic Line Item Custom Types
    LINE_ITEM_BUNDLE_CUSTOM_TYPE = 'lineItemsBundleCustomType'

    # BundleId custom field to store parent Bundle
    LINE_ITEM_BUNDLE_ID = 'bundleId'

    # Entitlement ID custom field to store with line item
    LINE_ITEM_LMS_ENTITLEMENT_ID = 'edxLMSEntitlementId'

    # Cart discount Custom Types
    CART_DISCOUNT_CUSTOM_TYPE = 'cartDiscountCustomType'

    # Client custom field to store in cart discount
    CART_DISCOUNT_CLIENT = 'client'

    # Category custom field to store in cart discount
    CART_DISCOUNT_CATEGORY = 'category'

    # Channel custom field to store in cart discount
    CART_DISCOUNT_CHANNEL = 'channel'

    # Discount Type custom field to store in cart discount
    CART_DISCOUNT_DISCOUNT_TYPE = 'discountType'

    # Cart/Order Custom Types - this is already used type, we are just updating it
    ORDER_CUSTOM_TYPE = 'cart-orderNumber'

    # Human readable order number field to store in cart/order model
    ORDER_ORDER_NUMBER = 'orderNumber'
    # Email domain custom field to store in cart/order model
    ORDER_EMAIL_DOMAIN = 'emailDomain'
    # Mobile order custom field to store in cart/order model
    ORDER_MOBILE_ORDER = 'mobileOrder'

    # Order number counter to store as a customer object
    ORDER_NUMBER_CUSTOM_OBJECT_CONTAINER = 'orderNumbers'
    ORDER_NUMBER_CUSTOM_OBJECT_KEY = 'orderNumber'


class CourseModes:
    """Course Mode keys for use in Commercetools"""

    # Course Modes
    AUDIT = 'audit'
    VERIFIED = 'verified'
    PROFESSIONAL = 'professional'
    CREDIT = 'credit'


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

PAYMENT_STATUS_INTERFACE_CODE_SUCCEEDED = "succeeded"

EDX_STRIPE_PAYMENT_INTERFACE_NAME = "stripe_edx"

EDX_PAYPAL_PAYMENT_INTERFACE_NAME = "paypal_edx"

# Payment types
ANDROID_IAP = "android_iap"
IOS_IAP = "ios_iap"

# Interface suffix
EDX_INTERFACE_SUFFIX = "_edx"

EDX_ANDROID_IAP_PAYMENT_INTERFACE_NAME = ANDROID_IAP + EDX_INTERFACE_SUFFIX

EDX_IOS_IAP_PAYMENT_INTERFACE_NAME = IOS_IAP + EDX_INTERFACE_SUFFIX

CART_DISCOUNT_TYPES = [
    {"key": "course-discount", "label": "Course Discount"},
    {"key": "enrollment-code", "label": "Enrollment Code"},
    {"key": "program-discount", "label": "Program Discount"},
    {"key": "program-offer", "label": "Program Offer"},
    {"key": "program-enrollment-code", "label": "Program Enrollment Code"}
]

# This mapping is based on prod categories
CART_DISCOUNT_CATEGORIES = [
    {"key": "affiliate-promotion", "label": "Affiliate Promotion"},
    {"key": "b2b-affiliate-promotion", "label": "B2B Affiliate Promotion"},
    {"key": "bulk-enrollment-prepay", "label": "Bulk Enrollment - Prepay"},
    {"key": "bulk-enrollment-upon-redemption", "label": "Bulk Enrollment - Upon Redemption"},
    {"key": "customer-service", "label": "Customer Service"},
    {"key": "financial-assistance", "label": "Financial Assistance"},
    {"key": "marketing-other", "label": "Marketing-Other"},
    {"key": "on-campus-learners", "label": "On-Campus Learners"},
    {"key": "partner-no-rev-prepay", "label": "Partner No Rev - Prepay"},
    {"key": "other", "label": "Other"}
]

CART_DISCOUNT_CHANNELS = [
    {"key": "affiliate", "label": "Affiliate"},
    {"key": "display-pmax", "label": "Display/PMAX"},
    {"key": "email", "label": "Email"},
    {"key": "enterprise-b2b", "label": "Enterprise/B2B"},
    {"key": "organic-edx", "label": "Organic/EdX"},
    {"key": "other", "label": "Other"},
]
