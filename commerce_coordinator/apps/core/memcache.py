"""
This module provides a KEY_FUNCTION suitable for use with a memcache backend
so that we can cache any keys, not just ones that memcache would ordinarily accept
"""

import hashlib
import logging
from urllib.parse import quote_plus

from django.utils.encoding import smart_str

# Memcache is done wiv TieredCache, here is an example:
#   https://github.com/openedx/edx-analytics-data-api/blob/824df06219a200ce688e973b2b115dd119f4526e/analytics_data_api/v0/views/learners.py#L32C1-L45C98
#       We are planning to use OUR safe_key() fn in this file instead of edx_django_utils.cache.get_cache_key()

MEMCACHE_KEY_LEN_MAX = 250
HASH_ALOG_LENGTH_LEN = 32

logger = logging.getLogger(__name__)


def fasthash(string):
    """
    Hashes `string` into a string representation of a 128-bit digest.

    Args:
        string (object): The value to hash
    """
    md5 = hashlib.new("md5")  # md4 is no longer supported.
    md5.update(string.encode('utf-8'))
    return md5.hexdigest()


def cleaned_string(val):
    """
    Converts `val` to unicode and URL-encodes special characters
    (including quotes and spaces)
    """
    return quote_plus(smart_str(val))


def safe_key(key, key_prefix, version):
    """
    Given a `key`, `key_prefix`, and `version`,
    return a key that is safe to use with memcache.

    `key`, `key_prefix`, and `version` can be numbers, strings, or unicode.

    Args:
        key_prefix (string): String for the key_prefix, version and version combined must be less than 216 chars
        version (string): String for the version, key_prefix and version combined must be less than 216 chars
        key (string): The specific Key for the Memcache entry
    """

    # Clean for whitespace and control characters, which
    # cause memcache to raise an exception
    key = cleaned_string(key)
    key_prefix = cleaned_string(key_prefix)
    version = cleaned_string(version)

    # Attempt to combine the prefix, version, and key
    key_ver = ":".join([key_prefix, version, ''])

    prefix_too_long = False

    if (len(key_ver) + 2) > MEMCACHE_KEY_LEN_MAX - HASH_ALOG_LENGTH_LEN:
        logger.warning("The key_prefix and version exceed %d characters, falling back to pure hashing, "
                       "this is not desired.", MEMCACHE_KEY_LEN_MAX - HASH_ALOG_LENGTH_LEN)
        prefix_too_long = True

    combined = f"{key_ver}{key}"

    # If the total length is too long for memcache, hash it
    if len(combined) > MEMCACHE_KEY_LEN_MAX:
        if prefix_too_long:
            combined = fasthash(combined)
        else:
            combined = f"{key_ver}{fasthash(combined)}"

    # Return the result
    return combined
