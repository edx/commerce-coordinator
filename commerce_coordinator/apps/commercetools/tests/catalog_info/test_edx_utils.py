"""Tests for edX Customization handlers for CoCo"""
import unittest
from typing import Union

from commercetools.platform.models import Customer as CTCustomer
from commercetools.platform.models import Order as CTOrder

from commerce_coordinator.apps.commercetools.catalog_info.edx_utils import (
    get_course_mode_from_ct_order,
    get_edx_items,
    get_edx_lms_user_id,
    get_edx_lms_user_name,
    get_edx_product_course_key,
    get_edx_product_course_run_key,
    is_edx_lms_order
)
from commerce_coordinator.apps.commercetools.tests.conftest import (
    DEFAULT_EDX_LMS_USER_ID,
    gen_customer,
    gen_order,
    gen_product
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

    def test_get_course_mode_from_ct_order(self):
        self.assertEqual(get_course_mode_from_ct_order(get_edx_items(self.order)[0]), 'certified')

    def test_get_edx_lms_user_id(self):
        self.assertEqual(get_edx_lms_user_id(self.user), DEFAULT_EDX_LMS_USER_ID)

    def test_get_edx_lms_user_name(self):
        self.assertEqual(get_edx_lms_user_name(self.user), _TEST_USER_NAME)


if __name__ == '__main__':
    unittest.main()
