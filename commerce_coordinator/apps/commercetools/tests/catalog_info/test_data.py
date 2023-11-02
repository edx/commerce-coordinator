import json
import uuid
from datetime import datetime
from typing import List, Optional
from unittest import TestCase

import ddt
from commercetools.platform.models import Address as CTAddress
from commercetools.platform.models import CartDiscountReference as CTCartDiscountReference
from commercetools.platform.models import Customer as CTCustomer
from commercetools.platform.models import DirectDiscount as CTDirectDiscount
from commercetools.platform.models import DiscountCode as CTDiscountCode
from commercetools.platform.models import DiscountCodeInfo as CTDiscountCodeInfo
from commercetools.platform.models import DiscountCodeReference as CTDiscountCodeReference
from commercetools.platform.models import DiscountCodeState as CTDiscountCodeState
from commercetools.platform.models import LineItem as CTLineItem
from commercetools.platform.models import Order as CTOrder
from commercetools.platform.models import PaymentInfo as CTPaymentInfo
from commercetools.platform.models import Reference as CTReference
from commercetools.platform.models import ReferenceTypeId as CTReferenceTypeId
from conftest import gen_order
from utils import name_test

from commerce_coordinator.apps.commercetools.catalog_info.constants import EdXFieldNames
from commerce_coordinator.apps.commercetools.catalog_info.utils import (
    attribute_dict,
    price_to_string,
    typed_money_add,
    typed_money_to_string,
    un_ls
)
from commerce_coordinator.apps.commercetools.data import (
    convert_address,
    convert_customer,
    convert_direct_discount,
    convert_discount_code_info,
    convert_line_item,
    convert_line_item_prod_id,
    convert_payment_info,
    order_from_commercetools
)
from commerce_coordinator.apps.ecommerce.data import BillingAddress, Line
from commerce_coordinator.apps.ecommerce.data import Order as LegacyOrder
from commerce_coordinator.apps.ecommerce.data import User


def gen_dci(code: str) -> CTDiscountCodeInfo:
    # 'id', 'version', 'created_at', 'last_modified_at', 'cart_discounts', 'is_active', 'references', and 'groups'
    dc_id = str(uuid.uuid4())
    return CTDiscountCodeInfo(
        discount_code=CTDiscountCodeReference(
            id=dc_id,
            obj=CTDiscountCode(
                code=code, id=dc_id, version=7, created_at=datetime.now(), last_modified_at=datetime.now(),
                is_active=True, references=[CTReference(type_id=CTReferenceTypeId.DISCOUNT_CODE, id=str(uuid.uuid4()))],
                groups=["xyzzy"], cart_discounts=[CTCartDiscountReference(id=str(uuid.uuid4()))]
            )
        ),
        state=CTDiscountCodeState.MATCHES_CART
    )

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
            "Valid Address",
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
    def test_convert_address(self, ct_address: CTAddress, bill_address: BillingAddress, is_none: bool):
        ret = convert_address(ct_address)

        if is_none:
            self.assertIsNone(ret)
        else:
            self.assertEqual(ret, bill_address)

    def test_convert_line_item(self):
        li = self.order.line_items[0]
        ret = convert_line_item(li)

        self.assertEqual(
            ret,
            Line(
                title=un_ls(li.name),
                quantity=li.quantity,
                course_organization="",
                description=un_ls(li.name),
                status="PAID",
                line_price_excl_tax=price_to_string(li.price),
                unit_price_excl_tax=price_to_string(li.price)
            )
        )

    @ddt.data(
        name_test(
            "Stripped",
            (True,)  # https://www.w3schools.com/python/gloss_python_tuple_one_item.asp
        ),
        name_test(
            "Set",
            (False,)
        )
    )
    def test_convert_line_item_prod_id(self, strip_custom_fields: bool):
        li: CTLineItem = self.order.line_items[0]

        if strip_custom_fields:
            li.variant.attributes = []

        ret = convert_line_item_prod_id(li)

        if strip_custom_fields:
            self.assertEqual(ret, li.product_id)
        else:
            attrs = attribute_dict(li.variant.attributes)
            self.assertEqual(ret, attrs['edx-course_run_id'])

    @ddt.data(
        name_test(
            "None",
            (
                None,
                None
            )
        ),
        name_test(
            "Empty",
            (
                [],
                None
            )
        ),
        name_test(
            "One",
            (
                [
                    gen_dci("Hiya")
                ],
                "Hiya"
            )
        ),
        name_test(
            "Two",
            (
                [
                    gen_dci("Hiya1"),
                    gen_dci("Hiya2")
                ],
                "Hiya1, Hiya2"
            )
        ),
    )
    @ddt.unpack
    def test_convert_discount_code_info(self, code_set:Optional[List[CTDiscountCodeInfo]], ret_string:Optional[str]):
        ret = convert_discount_code_info(code_set)
        self.assertEqual(ret, ret_string)

    # def test_convert_direct_discount(self):
    # def test_convert_customer(self):
    # def test_convert_payment_info(self):
    # def test_order_from_commercetools(self):
