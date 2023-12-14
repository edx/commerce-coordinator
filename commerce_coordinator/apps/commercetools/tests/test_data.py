""" Commercetools data conversion tests """
from datetime import datetime
from typing import List, Optional
from unittest import TestCase

import ddt
from commercetools.platform.models import Address as CTAddress
from commercetools.platform.models import AuthenticationMode as CTAuthenticationMode
from commercetools.platform.models import CartDiscountReference as CTCartDiscountReference
from commercetools.platform.models import CartDiscountValue as CTCartDiscountValue
from commercetools.platform.models import Customer as CTCustomer
from commercetools.platform.models import CustomFields as CTCustomFields
from commercetools.platform.models import DirectDiscount as CTDirectDiscount
from commercetools.platform.models import DiscountCode as CTDiscountCode
from commercetools.platform.models import DiscountCodeInfo as CTDiscountCodeInfo
from commercetools.platform.models import DiscountCodeReference as CTDiscountCodeReference
from commercetools.platform.models import DiscountCodeState as CTDiscountCodeState
from commercetools.platform.models import FieldContainer as CTFieldContainer
from commercetools.platform.models import LineItem as CTLineItem
from commercetools.platform.models import Reference as CTReference
from commercetools.platform.models import ReferenceTypeId as CTReferenceTypeId
from commercetools.platform.models import TypeReference as CTTypeReference

from commerce_coordinator.apps.commercetools.catalog_info.constants import EdXFieldNames
from commerce_coordinator.apps.commercetools.catalog_info.utils import attribute_dict, price_to_string, un_ls
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
from commerce_coordinator.apps.commercetools.tests.conftest import gen_customer, gen_order
from commerce_coordinator.apps.core.tests.utils import name_test, uuid4_str
from commerce_coordinator.apps.ecommerce.data import BillingAddress, Line
from commerce_coordinator.apps.ecommerce.data import Order as LegacyOrder


def gen_dci(code: str) -> CTDiscountCodeInfo:
    # 'id', 'version', 'created_at', 'last_modified_at', 'cart_discounts', 'is_active', 'references', and 'groups'
    dc_id = uuid4_str()
    return CTDiscountCodeInfo(
        discount_code=CTDiscountCodeReference(
            id=dc_id,
            obj=CTDiscountCode(
                code=code, id=dc_id, version=7, created_at=datetime.now(), last_modified_at=datetime.now(),
                is_active=True, references=[CTReference(type_id=CTReferenceTypeId.DISCOUNT_CODE, id=uuid4_str())],
                groups=["xyzzy"], cart_discounts=[CTCartDiscountReference(id=uuid4_str())]
            )
        ),
        state=CTDiscountCodeState.MATCHES_CART
    )


def gen_dd(code: str) -> CTDirectDiscount:
    return CTDirectDiscount(
        id=uuid4_str(),
        value=CTCartDiscountValue(
            type=code
        )
    )


@ddt.ddt
class TestCTOrderConversionToLegacyOrders(TestCase):
    """ Commercetools data conversion testcase to cover conversion functions in to legacy object formats """

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
        order = gen_order(uuid4_str())
        li = order.line_items[0]
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
        order = gen_order(uuid4_str())
        li: CTLineItem = order.line_items[0]

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
    def test_convert_discount_code_info(self, code_set: Optional[List[CTDiscountCodeInfo]], ret_string: Optional[str]):
        ret = convert_discount_code_info(code_set)
        self.assertEqual(ret, ret_string)

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
                    gen_dd("Hiya")
                ],
                "Hiya"
            )
        ),
        name_test(
            "Two",
            (
                [
                    gen_dd("Hiya1"),
                    gen_dd("Hiya2")
                ],
                "Hiya1, Hiya2"
            )
        ),
    )
    @ddt.unpack
    def test_convert_direct_discount(self, code_set: Optional[List[CTDirectDiscount]], ret_string: Optional[str]):
        ret = convert_direct_discount(code_set)
        self.assertEqual(ret, ret_string)

    def test_convert_customer(self):
        email = "someon@something.example"
        un = "steve_5"
        ret = convert_customer(CTCustomer(
            email=email,
            custom=CTCustomFields(
                type=CTTypeReference(
                    id=uuid4_str()
                ),
                fields=CTFieldContainer({EdXFieldNames.LMS_USER_NAME: un})
            ),
            version=3,
            addresses=[],
            authentication_mode=CTAuthenticationMode.PASSWORD,
            created_at=datetime.now(),
            id=uuid4_str(),
            is_email_verified=True,
            last_modified_at=datetime.now()
        ))

        self.assertEqual(ret.email, email)
        self.assertEqual(ret.username, un)

    def test_convert_payment_info(self):
        order = gen_order(uuid4_str())
        ret = convert_payment_info(order.payment_info)
        self.assertEqual(ret, "Mastercard")

    def test_convert_payment_info_when_empty(self):
        order = gen_order(uuid4_str())
        order.payment_info.payments = []
        ret = convert_payment_info(order.payment_info)
        self.assertEqual(ret, "Unknown")

    def test_order_from_commercetools(self):
        order = gen_order(uuid4_str())
        ret = order_from_commercetools(order, gen_customer("hiya@text.example", "jim_34"))

        self.assertIsInstance(ret, LegacyOrder)
        self.assertEqual(ret.currency, order.total_price.currency_code)
