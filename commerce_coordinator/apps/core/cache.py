"""
Core Cache utils.
"""
from enum import Enum

from edx_django_utils.cache import get_cache_key


class CachePaymentStates(Enum):
    PROCESSING = 'PROCESSING'
    PAID = 'PAID'


def get_payment_state_cache_key(payment_number, payment_state):
    """
    Wrapper method on edx_django_utils to payment_state_cache.
    """
    return get_cache_key(cache_name='payment', identifier=payment_number, version=payment_state)


def get_paid_payment_state_cache_key(payment_number):
    """
    Wrapper method on edx_django_utils to paid_payment_state_cache.
    """
    return get_payment_state_cache_key(payment_number=payment_number, payment_state=CachePaymentStates.PAID.value)


def get_processing_payment_state_cache_key(payment_number):
    """
    Wrapper method on edx_django_utils to processing_payment_state_cache.
    """
    return get_payment_state_cache_key(payment_number=payment_number, payment_state=CachePaymentStates.PROCESSING.value)
