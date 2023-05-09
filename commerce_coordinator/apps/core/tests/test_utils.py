"""Test the naming function? and other things in __init__"""

from unittest import TestCase

import ddt

from commerce_coordinator.apps.core.tests.utils import ANGRY_FACE, name_test, random_unicode_str


@ddt.ddt
class TestUtilFunctions(TestCase):
    """Utility Function tests"""

    @ddt.data(
        {"val": [1, 2, 3], "in_type": list, "class_name": "WrappedList"},
        {"val": ["1", 2, 3], "in_type": list, "class_name": "WrappedList"},
        {"val": ["1", {}, (), []], "in_type": list, "class_name": "WrappedList"},
        {"val": (1, 2, 3), "in_type": tuple, "class_name": "WrappedTuple"},
        {"val": ("1", 2, 3), "in_type": tuple, "class_name": "WrappedTuple"},
        {"val": ("1", {}, (), []), "in_type": tuple, "class_name": "WrappedTuple"},
        {"val": {"a": 1, "b": 2, "c": 3}, "in_type": dict, "class_name": "WrappedDict"},
        {"val": {"a": "1", "b": 2, "c": 3}, "in_type": dict, "class_name": "WrappedDict"},
        {"val": {"a": "1", "b": {}, "c": (), "d": []}, "in_type": dict, "class_name": "WrappedDict"},
    )
    @ddt.unpack
    def test_name_test(self, val, in_type, class_name):
        invalid_name_value = ANGRY_FACE  # angry face
        valid_name = random_unicode_str(32)  # '29920F96-373D-4F01-B2EA-1D57D47C62CC'  # a value that could be valid

        ntr = name_test(valid_name, val)

        # assert that type is subclass of the base type
        self.assertTrue(isinstance(ntr, in_type))
        # assert class is of the expected (hidden wrapper)
        self.assertEqual(class_name, ntr.__class__.__name__)
        # test the name matches
        self.assertEqual(valid_name, getattr(ntr, "__name__", invalid_name_value))
        # test sp that we don't lose items (incl native pointers) in back conversion.
        self.assertEqual(val, in_type(val))

    # (i): The random number testers use a hashing trick to take all the string values and use them in a dictionary then
    # counting the number of keys to know how many were unique. It's a simple shorthand.
    @ddt.data(
        # low numbers are very tricky, so skip here, and do a deviation check in another test
        (50, False),
        (500, False),
        (1000, False),
        (50, True),
        (500, True),
        (1000, True)
    )
    @ddt.unpack
    def test_random_unicode_str_randomness_over_time(self, strlen, limit_unicode):
        tries = 1000

        examples = dict(
            (hashed_string, True)  # kvp, val (True) is ignored
            for hashed_string in [
                random_unicode_str(strlen, limit_unicode=limit_unicode) for _ in range(tries)
            ]
        )

        self.assertEqual(tries, len(examples))

    @ddt.data(
        # low numbers are very tricky, so let's test a couple many times to see what happens
        1, 1, 1, 1,
        5, 5, 5, 5,
        7, 7, 7, 7,
        # hig nums are expensive let's run once
        50,
        500,
        1000
    )
    def test_random_unicode_str_diff_w_deviation_limit_unicode(self, strlen):
        self._random_unicode_str_diff_w_deviation(strlen, False)

    @ddt.data(
        # low numbers are less tricky with a whole character set, so let's test a couple many times to see what happens
        1, 1,
        5, 5,
        7, 7,
        # hig nums are expensive let's run once
        50,
        500,
        1000
    )
    def test_random_unicode_str_diff_w_deviation(self, strlen):
        self._random_unicode_str_diff_w_deviation(strlen, True)

    def _random_unicode_str_diff_w_deviation(self, strlen, limit_unicode):
        """ Because naming tests is so hard in DDT, i have separated this code path for clarity of reading results """

        deviation = 0.25  # percentage
        tries = 1000
        expected_results = tries - (tries * deviation)

        num_unichar = 29  # this is a magic number, just count uchars in `random_unicode_str()`

        if strlen * num_unichar < expected_results:
            expected_results = num_unichar - (num_unichar * deviation)

        examples = dict(
            (hashed_string, True)  # kvp, val (True) is ignored
            for hashed_string in [
                random_unicode_str(strlen, limit_unicode=limit_unicode) for _ in range(tries)
            ]
        )

        self.assertGreaterEqual(len(examples), abs(expected_results))
