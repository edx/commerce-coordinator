"""Test core.serializers."""

import datetime

import ddt
from django.test import TestCase

from commerce_coordinator.apps.core import serializers


utc = datetime.timezone.utc


@ddt.ddt
class UnixDateTimeFieldTests(TestCase):
    """Tests of UnixDateTimeField class."""

    @ddt.data(
        ("-1", datetime.datetime(1969, 12, 31, 23, 59, 59, tzinfo=utc)),
        ("0", datetime.datetime(1970, 1, 1, 00, 00, tzinfo=utc)),
        ("1680700901", datetime.datetime(2023, 4, 5, 13, 21, 41, tzinfo=utc)),
        (1680700901, datetime.datetime(2023, 4, 5, 13, 21, 41, tzinfo=utc)),
        (" 1680700901 ", datetime.datetime(2023, 4, 5, 13, 21, 41, tzinfo=utc)),
    )
    @ddt.unpack
    def test_valid_values(self, input_value, expected_output):
        """Check internal representation of UnixDateTimeField matches expected."""
        output = serializers.UnixDateTimeField().run_validation(input_value)
        self.assertEqual(output, expected_output)
