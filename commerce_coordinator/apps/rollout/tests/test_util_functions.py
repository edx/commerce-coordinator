from unittest import TestCase

import ddt
from utils import name_test

from commerce_coordinator.apps.rollout.utils import is_legacy_order, is_uuid


@ddt.ddt
class TestUtilityFunctions(TestCase):
    @ddt.data(
        name_test("test edx order num success", ("EDX-100001", True)),
        name_test("test uuid fails", ("03376B46-F737-4D16-8096-D2CEE39758E7", False)),
        name_test("test invalid", ("meow", False)),
        name_test("test tolerates none but fails", (None, False)),
        name_test("test tolerates blank but fails", ("", False)),
        name_test("test tolerates w/s but fails", ("  ", False)),
    )
    @ddt.unpack
    def test_is_legacy_order(self, value, expectation):
        self.assertEqual(is_legacy_order(value), expectation)

    @ddt.data(
        name_test("test uuid passes", ("03376B46-F737-4D16-8096-D2CEE39758E7", True)),
        name_test("test failure on edx order numbers", ("EDX-100001", False)),
        name_test("test invalid", ("meow", False)),
        name_test("test tolerates none but fails", (None, False)),
        name_test("test tolerates blank but fails", ("", False)),
        name_test("test tolerates w/s but fails", ("  ", False)),
    )
    @ddt.unpack
    def test_is_uuid(self, value, expectation):
        self.assertEqual(is_uuid(value), expectation)

