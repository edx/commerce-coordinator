""" Constants for the stripe app. """
from enum import Enum


class StripeEventType(str, Enum):
    """
    Enum for Stripe Payment Events.
    """
    PAYMENT_SUCCESS = 'payment_intent.succeeded'
    PAYMENT_FAILED = 'payment_intent.payment_failed'


class Currency(str, Enum):
    USD = 'usd'


class StripeErrorCode(str, Enum):
    CARD_DECLINED = 'card_declined'
