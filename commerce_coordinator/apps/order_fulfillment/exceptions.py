"""
Exceptions for Order Fulfillment API integration.
"""


class OrderFulfillmentRevokeLineError(Exception):
    """
    Raised when the Order Fulfillment revoke-line POST does not return a response.

    The client retries transient failures internally and returns None after exhausting
    retries, so callers should treat this as a failed revoke and allow Celery to retry.
    """
