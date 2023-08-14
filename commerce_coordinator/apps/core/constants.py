""" Constants for the core app. """
from enum import Enum


class Status:
    """Health statuses."""
    OK = "OK"
    UNAVAILABLE = "UNAVAILABLE"


class PaymentState(Enum):
    """
    Enum for Payment states, Controlled by Titan's System.
    """
    CHECKOUT = 'checkout'
    COMPLETED = 'completed'
    FAILED = 'failed'
    PENDING = 'pending'
    PROCESSING = 'processing'


class PaymentMethod(Enum):
    STRIPE = 'edX Stripe'


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
