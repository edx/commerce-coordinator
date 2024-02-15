""" Constants for the core app. """
from enum import Enum


class Status:
    """Health statuses."""
    OK = "OK"
    UNAVAILABLE = "UNAVAILABLE"


class OrderState(Enum):
    """
    Enum for order states.
    """
    CART = 'cart'
    ADDRESS = 'address'
    PAYMENT = 'payment'
    COMPLETE = 'complete'
    CANCELED = 'canceled'


class OrderPaymentState(Enum):
    """
    Enum for the state of payment of an order.
    """
    BALANCE_DUE = 'balance_due'
    FAILED = 'failed'
    PAID = 'paid'
    VOID = 'void'
    CREDIT_OWED = 'credit_owed'


class PaymentState(Enum):
    """
    Enum for Payment states, Controlled by Titan's System.
    """
    CHECKOUT = 'checkout'
    COMPLETED = 'completed'
    FAILED = 'failed'
    PENDING = 'pending'


class PaymentMethod(Enum):
    STRIPE = 'edX Stripe'


class PipelineCommand(Enum):
    """
    Special return values for openedx-filters PipelineStep.

    https://github.com/openedx/openedx-filters/blob/2d6b87b/openedx_filters/filters.py#L70-L75
    """

    CONTINUE = {}
    """Pass unaltered inputs to next pipeline step."""

    HALT = None
    """Abort any remaining pipeline steps for filter, returning the result of the previous steps (if any)."""


class QueryParamPrefixes(Enum):
    """Query Param Prefixes"""

    WAFFLE_FLAG = 'dwft_'
    """Django Waffle Flag"""

    GOOGLE_ANALYTICS = 'utm_'
    """Google Analytics (Urchin Tracking Module)"""


class WaffleFlagNames(Enum):
    """List of Waffle Flags"""

    COORDINATOR_ENABLED = 'transition_to_coordinator.order_create'
    """MFE Commerce Coordinator Flow Flag"""


class MediaTypes(Enum):
    """IANA Media Types (used to be called Mime-Types)"""

    JSON = 'application/json'


class HttpHeadersNames(Enum):
    """Standard HTTP Header Names"""

    CONTENT_TYPE = 'Content-type'
    """Set the Content Type of a Response"""

    CACHE_CONTROL = "Cache-Control"
    """Set the Caching Control info of a Response"""


ORDER_HISTORY_PER_SYSTEM_REQ_LIMIT = 200
"""The number of Order History items to pull per Catalog/Ordering System"""

UNIFIED_ORDER_HISTORY_RECEIPT_URL_KEY = 'receipt_url'
UNIFIED_ORDER_HISTORY_SOURCE_SYSTEM_KEY = 'source_system'
