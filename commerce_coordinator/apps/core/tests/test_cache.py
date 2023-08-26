""" Stripe Utils Tests"""
import unittest
from uuid import UUID

import ddt
from django.conf import settings
from edx_django_utils.cache import TieredCache
from rest_framework.exceptions import ErrorDetail, ValidationError

from commerce_coordinator.apps.core.cache import CacheBase, PaymentCache
from commerce_coordinator.apps.core.tests.utils import name_test


@ddt.ddt
class TestPaymentCache(unittest.TestCase):
    """
    Test class for PaymentCache.
    """
    def setUp(self) -> None:
        TieredCache.dangerous_clear_all_tiers()
        self.payment_number = '12345'
        self.payment = {
            'payment_number': self.payment_number,
            'order_uuid': UUID('123e4567-e89b-12d3-a456-426614174000'),
            'key_id': 'test-code',
            'new_payment_number': '67890',
            'state': 'a-paid-state',
        }
        self.payment_cache = PaymentCache()

    def test_error_on_using_base_cache_class(self):
        """
        Test error on using CacheBase directly.
        """
        with self.assertRaises(AssertionError) as ex:
            CacheBase()
        self.assertEqual(str(ex.exception), 'serializer_class override missing.')

    def test_get_cache_invalid_version(self):
        with self.assertRaises(AssertionError) as ex:
            self.payment_cache.get_cache_key(self.payment_number, 'invalid-state')
        self.assertEqual(
            str(ex.exception),
            "Invalid cache key version: invalid-state. Supported versions: ('PROCESSING', 'PAID')."
        )

    @ddt.data(
        name_test("test order_uuid in required", (
            {}, 'order_uuid',
            {'order_uuid': [ErrorDetail(string='This field is required.', code='required')]},
        )),
        name_test("test order_uuid format", (
            {'order_uuid': 'invalid-uuid'}, None,
            {'order_uuid': [ErrorDetail(string='Must be a valid UUID.', code='invalid')]},
        )),
        name_test("test key_id in required", (
            {}, 'key_id',
            {'key_id': [ErrorDetail(string='This field is required.', code='required')]},
        )),
        name_test("test payment_number in required", (
            {}, 'payment_number',
            {'payment_number': [ErrorDetail(string='This field is required.', code='required')]},
        )),
        name_test("test state in required", (
            {}, 'state',
            {'state': [ErrorDetail(string='This field is required.', code='required')]},
        )),
    )
    @ddt.unpack
    def test_cache_payment_error(self, update_params, skip_param, expected_error):
        """
        Test proper error on invalid data.
        """
        payment = {**self.payment}
        payment.update(update_params)
        if skip_param:
            del payment[skip_param]

        def _assert_error(payment_state):
            with self.assertRaises(ValidationError) as ex:
                self.payment_cache.set_cache(payment, payment_state)
            self.assertEqual(ex.exception.detail, expected_error)

            cache_key = self.payment_cache.get_cache_key(self.payment_number, payment_state)
            TieredCache.set_all_tiers(cache_key, payment, settings.DEFAULT_TIMEOUT)
            with self.assertRaises(ValidationError) as ex:
                self.payment_cache.get_cache(self.payment_number, payment_state)
            self.assertEqual(ex.exception.detail, expected_error)

        _assert_error(self.payment_cache.PAID)
        _assert_error(self.payment_cache.PROCESSING)

    def test_get_cache_payment(self):
        """
        Test PaymentCache setters and getters.
        """
        paid_payment = {**self.payment, 'state': 'a-paid-state'}
        processing_payment = {**self.payment, 'state': 'a-processing-state'}

        response = self.payment_cache.get_processing_cache_payment(self.payment_number)
        self.assertIsNone(response)
        self.payment_cache.set_processing_cache_payment(processing_payment)
        response = self.payment_cache.get_processing_cache_payment(self.payment_number)
        self.assertEqual(dict(response), processing_payment)

        # get_cache_payment should return PROCESSING payment. as we don't have PAID payment in cache.
        response = self.payment_cache.get_cache_payment(self.payment_number)
        self.assertEqual(dict(response), processing_payment)

        response = self.payment_cache.get_paid_cache_payment(self.payment_number)
        self.assertIsNone(response)
        self.payment_cache.set_paid_cache_payment(paid_payment)
        response = self.payment_cache.get_paid_cache_payment(self.payment_number)
        self.assertEqual(dict(response), paid_payment)

        # get_cache_payment should return PAID payment instead if PROCESSING payment.
        response = self.payment_cache.get_cache_payment(self.payment_number)
        self.assertEqual(dict(response), paid_payment)
        self.assertNotEqual(dict(response), processing_payment)
