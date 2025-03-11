""" Stripe Utils Tests"""
import unittest

import ddt

from commerce_coordinator.apps.stripe.utils import convert_dollars_in_cents, sanitize_provider_response_body


@ddt.ddt
class TestUtils(unittest.TestCase):
    """
    Test class for utils.
    """
    @ddt.data(
        (0.99, 99),
        (1, 100),
        (9.99, 999),
        ('50', 5000),
    )
    @ddt.unpack
    def test_convert_dollars_in_cents(self, dollars, expected_cents):
        """
        Test convert_dollars_in_cents utility.
        """
        self.assertEqual(convert_dollars_in_cents(dollars), expected_cents)

    @ddt.data(
        ({'key': 'value'}, {'key': 'value'}),
        ({'key': 'value', 'client_secret': 'top secret'}, {'key': 'value'}),
    )
    @ddt.unpack
    def test_sanitize_provider_response_body(self, provider_body, expected_provider_body):
        self.assertEqual(sanitize_provider_response_body(provider_body), expected_provider_body)
