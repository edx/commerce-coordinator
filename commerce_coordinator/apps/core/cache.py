"""
Core Cache utils.
"""
from enum import Enum

from django.conf import settings
from edx_django_utils.cache import TieredCache, get_cache_key

from commerce_coordinator.apps.titan.serializers import CachedPaymentSerializer


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


def set_payment_processing_cache(payment):
    """
    Utility for setting cache for the payment object in PROCESSING Cache.
    """
    cached_payment_serializer = CachedPaymentSerializer(data=payment)
    cached_payment_serializer.is_valid(raise_exception=True)
    payment = cached_payment_serializer.validated_data
    payment_state_processing_cache_key = get_processing_payment_state_cache_key(payment['payment_number'])
    TieredCache.set_all_tiers(payment_state_processing_cache_key, payment, settings.DEFAULT_TIMEOUT)


def set_payment_paid_cache(payment):
    """
    Utility for setting cache for the payment object in PAID Cache.
    """
    cached_payment_serializer = CachedPaymentSerializer(data=payment)
    cached_payment_serializer.is_valid(raise_exception=True)
    payment = cached_payment_serializer.data
    payment_state_paid_cache_key = get_paid_payment_state_cache_key(payment['payment_number'])
    TieredCache.set_all_tiers(payment_state_paid_cache_key, payment, settings.DEFAULT_TIMEOUT)


def get_payment_paid_cache(payment_number):
    """
    Utility for getting cache for the payment number from PROCESSING Cache.
    """
    payment_state_paid_cache_key = get_paid_payment_state_cache_key(payment_number)
    cached_response = TieredCache.get_cached_response(payment_state_paid_cache_key)
    if cached_response.is_found:
        cached_payment_serializer = CachedPaymentSerializer(data=cached_response.value)
        cached_payment_serializer.is_valid(raise_exception=True)
        return cached_payment_serializer.data
    return None


def get_payment_processing_cache(payment_number):
    """
    Utility for getting cache for the payment number from PAID Cache.
    """
    payment_state_processing_cache_key = get_processing_payment_state_cache_key(payment_number)
    cached_response = TieredCache.get_cached_response(payment_state_processing_cache_key)
    if cached_response.is_found:
        cached_payment_serializer = CachedPaymentSerializer(data=cached_response.value)
        cached_payment_serializer.is_valid(raise_exception=True)
        return cached_payment_serializer.data
    return None


def get_cached_payment(payment_number):
    """
    Utility to get cached payment.

    This utility is for getting cached payment. First tries to fetch it from PAID cache and then from PROCESSING Cache.
     Returns None otherwise.
    """
    return get_payment_paid_cache(payment_number) or get_payment_processing_cache(payment_number)
