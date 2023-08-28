"""
Core Cache utils.
"""

from django.conf import settings
from edx_django_utils.cache import TieredCache, get_cache_key

from commerce_coordinator.apps.titan.serializers import CachedPaymentSerializer


class CacheBase:
    """
    Base class for versioned cache. Extend this class to create custom cache.
    """
    serializer_class = None
    cache_name = ''
    identifier_key = ''
    versions = ()

    def __init__(self):
        assert self.serializer_class, 'serializer_class override missing.'
        assert self.cache_name, 'cache_name override missing.'
        assert self.identifier_key, 'identifier_key override missing.'
        assert self.versions, 'versions override missing.'

    def get_cache_key(self, identifier, version):
        """
        Wrapper method on edx_django_utils to get cache_key.
        """
        assert version in self.versions, f'Invalid cache key version: {version}. Supported versions: {self.versions}.'
        return get_cache_key(cache_name=self.cache_name, version=version, identifier=identifier)

    def set_cache(self, data, version):
        """
        Utility for caching data for given cache version
        """
        serializer = self.serializer_class(data=data)  # pylint: disable=not-callable
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        cache_key = self.get_cache_key(data[self.identifier_key], version)
        TieredCache.set_all_tiers(cache_key, data, settings.DEFAULT_TIMEOUT)

    def get_cache(self, identifier, version):
        """
        Utility for getting cache data for given cache version
        """
        cache_key = self.get_cache_key(identifier, version)
        cached_response = TieredCache.get_cached_response(cache_key)
        if cached_response.is_found:
            serializer = self.serializer_class(data=cached_response.value)  # pylint: disable=not-callable
            serializer.is_valid(raise_exception=True)
            return serializer.validated_data
        return None


class PaymentCache(CacheBase):
    """
    Cache class for payment data.
    """
    PROCESSING = 'PROCESSING'
    PAID = 'PAID'
    versions = (PROCESSING, PAID)
    serializer_class = CachedPaymentSerializer
    identifier_key = 'payment_number'
    cache_name = 'payment'

    def set_paid_cache_payment(self, payment):
        self.set_cache(payment, self.PAID)

    def set_processing_cache_payment(self, payment):
        self.set_cache(payment, self.PROCESSING)

    def get_paid_cache_payment(self, payment_number):
        return self.get_cache(payment_number, self.PAID)

    def get_processing_cache_payment(self, payment_number):
        return self.get_cache(payment_number, self.PROCESSING)

    def get_cache_payment(self, payment_number):
        """
        Utility to get cached payment.

        This utility is for getting cached payment. First tries to fetch it from PAID cache and
         then from PROCESSING Cache. Returns None otherwise.
        """
        return self.get_paid_cache_payment(payment_number) or self.get_processing_cache_payment(payment_number)
