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
