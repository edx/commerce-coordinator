"""Test core.serializers."""

import datetime
import sys

import ddt
from django.test import TestCase

from commerce_coordinator.apps.core import serializers

utc = datetime.timezone.utc


class CoordinatorSerializerTests(TestCase):
    """Tests of the CoordinatorSerializer class."""

    def test_create_exception(self):
        with self.assertRaises(TypeError):
            serializers.CoordinatorSerializer().create({})

    def test_update_exception(self):
        with self.assertRaises(TypeError):
            serializers.CoordinatorSerializer().update({}, {})


@ddt.ddt
class UnixDateTimeFieldTests(TestCase):
    """Tests of UnixDateTimeField class."""

    @ddt.data(
        ("-1", datetime.datetime(1969, 12, 31, 23, 59, 59, tzinfo=utc)),
        ("0", datetime.datetime(1970, 1, 1, 00, 00, tzinfo=utc)),
        ("1680700901", datetime.datetime(2023, 4, 5, 13, 21, 41, tzinfo=utc)),
        (1680700901, datetime.datetime(2023, 4, 5, 13, 21, 41, tzinfo=utc)),
        (" 1680700901 ", datetime.datetime(2023, 4, 5, 13, 21, 41, tzinfo=utc)),
        ("1680700901.999999", datetime.datetime(2023, 4, 5, 13, 21, 41, 999999, tzinfo=utc)),
    )
    @ddt.unpack
    def test_valid_values(self, input_value, expected_output):
        """Check internal representation of UnixDateTimeField matches expected."""
        output = serializers.UnixDateTimeField().run_validation(input_value)
        self.assertEqual(output, expected_output)

    @ddt.data(
        ('not_a_date', ['A valid number is required.']),
        (sys.maxsize, ['Could not parse POSIX timestamp.']),
        ('long_string' * 91, ['String value too large.']),
    )
    @ddt.unpack
    def test_invalid_values(self, input_value, expected_failure_message):
        """Check failures of conversion of internal representation of UnixDateTimeField produce expected errors."""
        with self.assertRaises(serializers.ValidationError) as exc_info:
            serializers.UnixDateTimeField().run_validation(input_value)

        self.assertEqual(exc_info.exception.detail, expected_failure_message)
