""" Commcercetools API Utilities """
from typing import Union
from unittest import TestCase

import ddt
import pytest
from commercetools.platform.models import CentPrecisionMoney, HighPrecisionMoney
from commercetools.platform.models import Order as CTOrder
from commercetools.platform.models import Price
from currencies import Currency

from commerce_coordinator.apps.commercetools.catalog_info.constants import Languages
from commerce_coordinator.apps.commercetools.catalog_info.edx_utils import get_edx_items
from commerce_coordinator.apps.commercetools.catalog_info.utils import (
    attribute_dict,
    get_course_mode_from_ct_order,
    ls,
    ls_eq,
    price_to_string,
    typed_money_add,
    typed_money_to_string,
    un_ls
)
from commerce_coordinator.apps.commercetools.tests.conftest import gen_order
from commerce_coordinator.apps.core.tests.utils import name_test, uuid4_str

# <Country>_<Currency>
JAPAN_YEN = "JPY"  # 0 fractional digits
# There is no current currency with only one fractional digit
US_DOLLAR = "USD"  # 2 fractional digits
OMAN_RIAL = "OMR"  # 3 fractional digits


@ddt.ddt
class LocalizedStringsTests(TestCase):
    """ Localized String Utility Tests"""

    order: Union[CTOrder, None]

    def setUp(self):
        self.order = gen_order(uuid4_str())
        super().setUp()

    def tearDown(self):
        self.order = None
        super().tearDown()

    # ls()
    def test_single_unknown_key_ls_creation(self):
        string = "test"
        result = ls({'ZZ': string})
        self.assertEqual(result, {'ZZ': string, Languages.ENGLISH: string, Languages.US_ENGLISH: string})

    def test_get_course_mode_from_ct_order(self):
        self.assertEqual(get_course_mode_from_ct_order(get_edx_items(self.order)[0]), 'professional')

    def test_single_key_ls_creation(self):
        string = "test-2"
        result = ls({Languages.ENGLISH: string})
        self.assertEqual(result, {Languages.ENGLISH: string, Languages.US_ENGLISH: string})

    def test_two_key_ls_us_creation(self):
        string = "test-3"
        result = ls({Languages.ENGLISH: string, Languages.US_ENGLISH: string})
        self.assertEqual(result, {Languages.ENGLISH: string, Languages.US_ENGLISH: string})

    # un_ls()
    @ddt.data(
        ({Languages.ENGLISH: "abc"}, "abc"),
        ({Languages.US_ENGLISH: "abc"}, "abc"),
        ({Languages.US_ENGLISH: "abc", Languages.ENGLISH: "xyz"}, "xyz"),
        ({'ZZ': "abc", Languages.ENGLISH: "xyz"}, "xyz"),
        ({'ZZ': "abc"}, "abc"),
        ({}, None)
    )
    @ddt.unpack
    def test_un_ls_default_preference(self, ls_struct, expected):
        result = un_ls(ls_struct)
        self.assertEqual(result, expected)

    @ddt.data(
        ({Languages.ENGLISH: "abc"}, "abc", Languages.ENGLISH),
        ({Languages.US_ENGLISH: "abc"}, "abc", Languages.US_ENGLISH),
        ({Languages.US_ENGLISH: "abc", Languages.ENGLISH: "xyz"}, "abc", Languages.US_ENGLISH),
        ({'ZZ': "abc", Languages.ENGLISH: "xyz"}, "abc", 'ZZ'),
        ({'ZZ': "abc"}, "abc", Languages.ENGLISH),
        ({'ZZ': "abc", 'XX': "xyz"}, "abc", Languages.ENGLISH)
    )
    @ddt.unpack
    def test_un_ls_set_preference(self, ls_struct, expected, pref):
        result = un_ls(ls_struct, pref)
        self.assertEqual(result, expected)

    def test_un_ls_with_none_string_dict(self):
        result = un_ls(None)
        self.assertIsNone(result)

    @ddt.data(
        ({Languages.ENGLISH: "abc"}, {Languages.ENGLISH: "abc"}, True),
        ({Languages.US_ENGLISH: "abc"}, {Languages.ENGLISH: "xyz"}, False),
        (None, {Languages.ENGLISH: "xyz"}, False),
        ({Languages.ENGLISH: "xyz"}, None, False),
    )
    @ddt.unpack
    def test_ls_eq(self, a, b, is_same):
        self.assertEqual(ls_eq(a, b), is_same)

    def test_attribute_dict(self):
        self.assertEqual(attribute_dict(None), None)


@ddt.ddt
class PriceAndMoneyTests(TestCase):
    """ Test the Price and Money utility functions """

    # price_to_string
    @ddt.data(
        name_test(US_DOLLAR,
                  (
                      Price(
                          id="c4d32806-adbd-482f-b5d2-03b2016e2c95", key="edx-usd_price-8CF08E5",
                          value=CentPrecisionMoney(
                              cent_amount=14900,
                              currency_code=US_DOLLAR,
                              fraction_digits=2
                          )
                      ),
                      US_DOLLAR, 149.00
                  )),
        name_test(JAPAN_YEN,
                  (
                      Price(
                          id="c4d32806-adbd-482f-b5d2-03b2016e2c96", key="edx-usd_price-8CF08E6",
                          value=CentPrecisionMoney(
                              cent_amount=14900,
                              currency_code=JAPAN_YEN,
                              fraction_digits=0
                          )
                      ),
                      JAPAN_YEN, 14900
                  )),
        name_test(OMAN_RIAL,
                  (
                      Price(
                          id="c4d32806-adbd-482f-b5d2-03b2016e2c97", key="edx-usd_price-8CF08E57",
                          value=CentPrecisionMoney(
                              cent_amount=14900,
                              currency_code=OMAN_RIAL,
                              fraction_digits=3
                          )
                      ),
                      OMAN_RIAL, 14.900
                  ))
    )
    @ddt.unpack
    def test_price_to_string(self, price, curr_code, numeric_price):
        curr_conv = Currency(curr_code)
        result = price_to_string(price)
        self.assertEqual(result, curr_conv.get_money_format(numeric_price))

    # typed_money_to_string
    @ddt.data(
        name_test(US_DOLLAR,
                  (
                      CentPrecisionMoney(
                          cent_amount=14900,
                          currency_code=US_DOLLAR,
                          fraction_digits=2
                      ),
                      US_DOLLAR, 149.00
                  )),
        name_test(JAPAN_YEN,
                  (
                      CentPrecisionMoney(
                          cent_amount=14900,
                          currency_code=JAPAN_YEN,
                          fraction_digits=0
                      ),
                      JAPAN_YEN, 14900
                  )),
        name_test(OMAN_RIAL,
                  (
                      CentPrecisionMoney(
                          cent_amount=14900,
                          currency_code=OMAN_RIAL,
                          fraction_digits=3
                      ),
                      OMAN_RIAL, 14.900
                  ))
    )
    @ddt.unpack
    def test_typed_money_to_string_cents(self, tm, curr_code, numeric_price):
        curr_conv = Currency(curr_code)
        result = typed_money_to_string(tm)
        self.assertEqual(result, curr_conv.get_money_format(numeric_price))

    @ddt.data(  # taken from table at the end of https://docs.commercetools.com/api/types#usage
        [123456, 3, 123.456, US_DOLLAR, '$123.456'],
        [123456, 5, 1.23456, US_DOLLAR, '$1.23456'],
        [123456, 7, 0.0123456, US_DOLLAR, '$0.0123456']
    )
    @ddt.unpack
    def test_typed_money_to_string_high(self, precision, fract_digi, actual, curr_code, str_match):
        curr_conv = Currency(curr_code)
        result = typed_money_to_string(HighPrecisionMoney(
            fraction_digits=fract_digi,
            precise_amount=precision,
            currency_code=curr_code,
            cent_amount=1
        ))
        self.assertEqual(result, curr_conv.get_money_format(actual))
        self.assertEqual(result, str_match)

    @ddt.data(
        name_test(
            f"{US_DOLLAR} + {JAPAN_YEN} fails",
            (
                CentPrecisionMoney(
                    cent_amount=14900,
                    currency_code=US_DOLLAR,
                    fraction_digits=2
                ),
                CentPrecisionMoney(
                    cent_amount=14900,
                    currency_code=JAPAN_YEN,
                    fraction_digits=0
                ),
                True
            )
        ),
        name_test(
            f"{US_DOLLAR} + {OMAN_RIAL} fails",
            (
                CentPrecisionMoney(
                    cent_amount=14900,
                    currency_code=US_DOLLAR,
                    fraction_digits=2
                ),
                HighPrecisionMoney(
                    cent_amount=1,
                    currency_code=OMAN_RIAL,
                    fraction_digits=0,
                    precise_amount=123
                ),
                True
            )
        ),
        name_test(
            f"{OMAN_RIAL} + {OMAN_RIAL} passes",
            (
                HighPrecisionMoney(
                    cent_amount=1,
                    currency_code=OMAN_RIAL,
                    fraction_digits=0,
                    precise_amount=123
                ),
                HighPrecisionMoney(
                    cent_amount=1,
                    currency_code=OMAN_RIAL,
                    fraction_digits=0,
                    precise_amount=123
                ),
                False
            )
        ),
        name_test(
            f"{US_DOLLAR} + {US_DOLLAR} passes",
            (
                CentPrecisionMoney(
                    cent_amount=14900,
                    currency_code=US_DOLLAR,
                    fraction_digits=2
                ),
                CentPrecisionMoney(
                    cent_amount=14900,
                    currency_code=US_DOLLAR,
                    fraction_digits=2
                ),
                False
            )
        )
    )
    @ddt.unpack
    def test_typed_money_add(self, a, b, err):
        if err:
            with pytest.raises(ValueError) as _:
                _ = typed_money_add(a, b)
        else:
            if isinstance(a, HighPrecisionMoney):
                hpm_ret = typed_money_add(a, b)
                self.assertEqual(a.precise_amount + b.precise_amount, hpm_ret.precise_amount)
            else:
                cpm_ret = typed_money_add(a, b)
                self.assertEqual(a.cent_amount + b.cent_amount, cpm_ret.cent_amount)
