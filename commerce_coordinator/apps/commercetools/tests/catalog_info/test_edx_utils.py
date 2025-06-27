"""Tests for edX Customization handlers for CoCo"""
import decimal
import unittest
from typing import Union

from commercetools.platform.models import Attribute, CentPrecisionMoney
from commercetools.platform.models import Customer as CTCustomer
from commercetools.platform.models import Order as CTOrder
from commercetools.platform.models import TransactionType

from commerce_coordinator.apps.commercetools.catalog_info.edx_utils import (
    get_attribute_value,
    get_edx_items,
    get_edx_lms_user_id,
    get_edx_lms_user_name,
    get_edx_product_course_key,
    get_edx_product_course_run_key,
    get_edx_refund_info,
    get_line_item_price_to_refund,
    is_edx_lms_order,
    sum_money
)
from commerce_coordinator.apps.commercetools.tests.conftest import (
    DEFAULT_EDX_LMS_USER_ID,
    gen_customer,
    gen_order,
    gen_payment,
    gen_product,
    gen_program_order
)
from commerce_coordinator.apps.core.tests.utils import uuid4_str

_TEST_USER_NAME = "jdoe22"


class TestEdXFunctions(unittest.TestCase):
    """Test for edx_utils"""
    order: Union[CTOrder, None]
    user: Union[CTCustomer, None]

    def setUp(self):
        self.order = gen_order(uuid4_str())
        self.user = gen_customer("email@example.com", _TEST_USER_NAME)
        super().setUp()

    def tearDown(self):
        self.order = None
        self.user = None
        super().tearDown()

    def test_get_edx_product_course_run_key(self):
        li = self.order.line_items[0]
        prodvar = li.variant

        self.assertEqual(get_edx_product_course_run_key(prodvar), prodvar.sku)
        self.assertEqual(get_edx_product_course_run_key(li), prodvar.sku)

    def test_get_edx_product_course_key(self):
        li = self.order.line_items[0]
        prod = gen_product()
        self.assertEqual(get_edx_product_course_key(prod), "MichiganX+InjuryPreventionX")
        self.assertEqual(get_edx_product_course_key(li), "MichiganX+InjuryPreventionX")

    def test_get_edx_items(self):
        self.assertEqual(len(get_edx_items(self.order)), 1)

    def test_is_edx_lms_order(self):
        self.assertTrue(is_edx_lms_order(self.order))

    def test_get_edx_lms_user_id(self):
        self.assertEqual(get_edx_lms_user_id(self.user), DEFAULT_EDX_LMS_USER_ID)

    def test_get_edx_lms_user_name(self):
        self.assertEqual(get_edx_lms_user_name(self.user), _TEST_USER_NAME)

    def test_get_edx_refund_info(self):
        payment = gen_payment()
        payment.transactions[0].interaction_id = "test_interaction_id"
        payment.transactions[0].type = TransactionType.CHARGE
        order = self.order
        return_line_item_id = order.line_items[0].id

        refund_amount, interaction_id = get_edx_refund_info(payment, order, return_line_item_id)

        self.assertEqual(refund_amount, decimal.Decimal(order.line_items[0].total_price.cent_amount / 100))
        self.assertEqual(interaction_id, "test_interaction_id")

    def test_get_line_item_price_to_refund_single_item(self):
        order = gen_order(uuid4_str())
        line_item_id = order.line_items[0].id
        expected_refund_amount = decimal.Decimal(order.line_items[0].total_price.cent_amount / 100)

        refund_amount = get_line_item_price_to_refund(order, [line_item_id])

        self.assertEqual(refund_amount, expected_refund_amount)

    def test_get_line_item_price_to_refund_bundle(self):
        order = gen_program_order(uuid4_str())
        line_item_id = order.line_items[0].id
        expected_refund_amount = decimal.Decimal(order.line_items[0].total_price.cent_amount / 100)

        refund_amount = get_line_item_price_to_refund(order, line_item_id)

        self.assertEqual(refund_amount, expected_refund_amount)

    def test_get_line_item_price_to_refund_nonexistent_item(self):
        order = gen_program_order(uuid4_str())
        non_existent_line_item_id = "non_existent_id"
        expected_refund_amount = decimal.Decimal(0)

        refund_amount = get_line_item_price_to_refund(order, [non_existent_line_item_id])

        self.assertEqual(refund_amount, expected_refund_amount)


class TestSumMoney(unittest.TestCase):
    """Tests for sum_money utility function"""

    def test_sum_money_with_valid_money_objects(self):
        """Test summing multiple valid CentPrecisionMoney objects"""

        money1 = CentPrecisionMoney(cent_amount=1000, currency_code="USD", fraction_digits=2)
        money2 = CentPrecisionMoney(cent_amount=2500, currency_code="USD", fraction_digits=2)
        money3 = CentPrecisionMoney(cent_amount=7500, currency_code="USD", fraction_digits=2)

        result = sum_money(money1, money2, money3)

        assert result.cent_amount == 11000
        assert result.currency_code == "USD"
        assert result.fraction_digits == 2

    def test_sum_money_with_none_values(self):
        """Test summing with None values and edge cases"""

        money1 = CentPrecisionMoney(cent_amount=1000, currency_code="USD", fraction_digits=2)
        money2 = None

        result = sum_money(money1, money2)
        assert result.cent_amount == 1000
        assert result.currency_code == "USD"
        assert result.fraction_digits == 2

        result = sum_money(None, None)
        assert result is None

        result = sum_money()
        assert result is None


class TestGetAttributeValue(unittest.TestCase):
    """Tests for get_attribute_value utility function"""

    def test_get_attribute_value_found(self):
        """Test retrieving attribute values that exist in the list"""

        attributes = [
            Attribute(name="color", value="red"),
            Attribute(name="size", value="medium"),
            Attribute(name="price", value=19.99),
            Attribute(name="in_stock", value=True)
        ]

        result1 = get_attribute_value(attributes, "color")
        assert result1 == "red"

        result2 = get_attribute_value(attributes, "size")
        assert result2 == "medium"

        result3 = get_attribute_value(attributes, "price")
        assert result3 == 19.99

        result4 = get_attribute_value(attributes, "in_stock")
        assert result4 is True

    def test_get_attribute_value_edge_cases(self):
        """Test edge cases for get_attribute_value function"""

        attributes = [
            Attribute(name="empty", value=""),
            Attribute(name="zero", value=0),
            Attribute(name="none_value", value=None)
        ]

        result1 = get_attribute_value(attributes, "non_existent")
        assert result1 is None

        result2 = get_attribute_value(attributes, "empty")
        assert result2 == ""

        result3 = get_attribute_value(attributes, "zero")
        assert result3 == 0

        result4 = get_attribute_value(attributes, "none_value")
        assert result4 is None

        result5 = get_attribute_value([], "any_key")
        assert result5 is None


if __name__ == '__main__':
    unittest.main()
