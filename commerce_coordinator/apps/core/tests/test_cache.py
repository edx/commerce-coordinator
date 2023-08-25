""" Stripe Utils Tests"""
import unittest

import ddt
from edx_django_utils.cache import TieredCache

from commerce_coordinator.apps.core import cache


@ddt.ddt
class TestCacheUtils(unittest.TestCase):
    """
    Test class for cache utils.
    """
    def setUp(self) -> None:
        self.payment_number = '12345'
        self.payment = {
            'payment_number': self.payment_number,
            'order_uuid': '123e4567-e89b-12d3-a456-426614174000',
            'key_id': 'test-code',
            'state': 'a-payment_state',
            'new_payment_number': '67890'
        }
        TieredCache.dangerous_clear_all_tiers()

    def test_payment_cache(self):
        """
        Test units by setting cache and setting cache
        """
        cached_payment = cache.get_payment_processing_cache(self.payment_number)
        self.assertIsNone(cached_payment)
        cache.set_payment_processing_cache(self.payment)
        cached_payment = cache.get_payment_processing_cache(self.payment_number)
        self.assertEqual(cached_payment, self.payment)

        cached_payment = cache.get_payment_paid_cache(self.payment_number)
        self.assertIsNone(cached_payment)
        cache.set_payment_paid_cache(self.payment)
        cached_payment = cache.get_payment_paid_cache(self.payment_number)
        self.assertEqual(cached_payment, self.payment)

        cached_payment = cache.get_cached_payment(self.payment_number)
        self.assertEqual(cached_payment, self.payment)
