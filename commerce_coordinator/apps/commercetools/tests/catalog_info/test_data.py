import uuid
from typing import Optional
from unittest import TestCase

import ddt

from commercetools.platform.models import Address as CTAddress
from commercetools.platform.models import Customer as CTCustomer
from commercetools.platform.models import DirectDiscount as CTDirectDiscount
from commercetools.platform.models import DiscountCodeInfo as CTDiscountCodeInfo
from commercetools.platform.models import LineItem as CTLineItem
from commercetools.platform.models import Order as CTOrder
from commercetools.platform.models import PaymentInfo as CTPaymentInfo

from commerce_coordinator.apps.commercetools.catalog_info.constants import EdXFieldNames
from commerce_coordinator.apps.commercetools.catalog_info.utils import (
    attribute_dict,
    price_to_string,
    typed_money_add,
    typed_money_to_string,
    un_ls
)
from commerce_coordinator.apps.ecommerce.data import BillingAddress, Line
from commerce_coordinator.apps.ecommerce.data import Order as LegacyOrder
from commerce_coordinator.apps.ecommerce.data import User

from commerce_coordinator.apps.commercetools.data import convert_address
from conftest import gen_order
from utils import name_test


@ddt.ddt
class TestCTOrderConversionToLegacyOrders(TestCase):
    order: Optional[CTOrder] = None

    def setUp(self):
        super().setUp()
        self.order = gen_order(str(uuid.uuid4()))

    @ddt.data(
        name_test(
            "None",
            (
                None,
                None,
                True
            )
        ),
        name_test(
            "Address",
            (
                CTAddress(
                    first_name="Jean Luc",
                    last_name="Pikachu",
                    street_number="12",
                    street_name="Any St.",
                    additional_street_info="Suite 456",
                    postal_code="101-0054",
                    state="MA",
                    country="USA",
                    city="Cambridge"
                ),
                BillingAddress(
                    first_name="Jean Luc",
                    last_name="Pikachu",
                    line1="12 Any St.",
                    line2="Suite 456",
                    postcode="101-0054",
                    state="MA",
                    country="USA",
                    city="Cambridge"
                ),
                False
            )
        ),
    )
    @ddt.unpack
    def test_convert_address(self, ctaddress: CTAddress, billaddress: BillingAddress, is_none:bool):
        ret = convert_address(ctaddress)

        if is_none:
            self.assertIsNone(ret)
        else:
            self.assertEqual(ret, billaddress)

    # def test_convert_line_item(self):
    # def test_convert_line_item_prod_id(self):
    # def test_convert_discount_code_info(self):
    # def test_convert_direct_discount(self):
    # def test_convert_customer(self):
    # def test_convert_payment_info(self):
    # def test_order_from_commercetools(self):
