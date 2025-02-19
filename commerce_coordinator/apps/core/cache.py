"""
Core Cache utils.
"""

from django.conf import settings
from edx_django_utils.cache import TieredCache, get_cache_key


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
