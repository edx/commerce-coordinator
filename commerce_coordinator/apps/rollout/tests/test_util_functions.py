from unittest import TestCase

import ddt
from commercetools.platform.models import ReturnInfo, ReturnPaymentState

from commerce_coordinator.apps.commercetools.tests.conftest import gen_order, gen_return_item
from commerce_coordinator.apps.core.tests.utils import name_test, uuid4_str
from commerce_coordinator.apps.rollout.utils import (
    get_order_return_info_return_items,
    is_commercetools_line_item_already_refunded,
    is_legacy_order,
    is_uuid
)


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
        name_test("test uc uuid passes", ("03376B46-F737-4D16-8096-D2CEE39758E7", True)),
        name_test("test lc uuid passes", ("5f274348-2559-4c36-9ad0-6b99c270ea53", True)),
        name_test("test failure on edx order numbers", ("EDX-100001", False)),
        name_test("test invalid", ("meow", False)),
        name_test("test tolerates none but fails", (None, False)),
        name_test("test tolerates blank but fails", ("", False)),
        name_test("test tolerates w/s but fails", ("  ", False)),
    )
    @ddt.unpack
    def test_is_uuid(self, value, expectation):
        self.assertEqual(is_uuid(value), expectation)

    def test_get_order_return_info_return_items(self):
        order = gen_order(uuid4_str())

        self.assertEqual(len(get_order_return_info_return_items(order)), 2)

    @ddt.data(
            {'line_item_id': 'order_line_id'}
    )
    @ddt.unpack
    def test_is_commercetools_line_item_already_refunded(self, line_item_id):
        order = gen_order(uuid4_str())
        mock_response_return_item = gen_return_item("order_line_id", ReturnPaymentState.REFUNDED)
        mock_response_return_info = ReturnInfo(items=[mock_response_return_item])
        order.return_info.append(mock_response_return_info)

        self.assertTrue(is_commercetools_line_item_already_refunded(order, line_item_id))
