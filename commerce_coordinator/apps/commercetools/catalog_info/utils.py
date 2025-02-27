from typing import Dict, List, Optional, Union

from commercetools.platform.models import Attribute as CTAttribute
from commercetools.platform.models import CentPrecisionMoney as CTCentPrecisionMoney
from commercetools.platform.models import HighPrecisionMoney as CTHighPrecisionMoney
from commercetools.platform.models import LineItem as CTLineItem
from commercetools.platform.models import LocalizedString as CTLocalizedString
from commercetools.platform.models import MoneyType as CTMoneyType
from commercetools.platform.models import Price as CTPrice
from commercetools.platform.models import TypedMoney as CTTypedMoney
from currencies import Currency

from commerce_coordinator.apps.commercetools.catalog_info.constants import (
    HIDE_CODE_FOR_CURRENCIES,
    LS_OUT_PREFERENCES,
    SEND_MONEY_AS_DECIMAL_STRING,
    Languages,
    TwoUKeys
)

LSLike = Union[Dict[str, str], CTLocalizedString]


def ls(string_dict: LSLike) -> CTLocalizedString:
    """ Make a LocalizedString that doesn't freak out type checking, assign en to en-US as well. """
    if len(string_dict) == 1 and Languages.ENGLISH not in string_dict:
        # If we don't have english, this still needs to show for IT and Support in the UI
        string_dict[Languages.ENGLISH] = string_dict[list(string_dict.keys())[0]]

    if Languages.ENGLISH in string_dict and Languages.US_ENGLISH not in string_dict:
        # Keys are CASE sensitive. String matching the pattern ^[a-z]{2}(-[A-Z]{2})?$ representing an IETF language tag
        string_dict[Languages.US_ENGLISH] = string_dict[Languages.ENGLISH]

    return string_dict


def get_line_item_attribute(in_line_item, in_attribute_name):  # pragma no cover
    """Utility to get line item's attribute's value."""
    attribute_value = None
    for attribute in in_line_item.variant.attributes:
        if attribute.name == in_attribute_name and hasattr(attribute, 'value'):
            if isinstance(attribute.value, dict):
                attribute_value = attribute.value.get('label', None)
            elif isinstance(attribute.value, str):
                attribute_value = attribute.value
            break

    return attribute_value


def get_course_mode_from_ct_order(line_item: CTLineItem, is_bundle=False) -> str:
    mode_attribute = 'entitlement-mode' if is_bundle else 'mode'
    course_mode = get_line_item_attribute(line_item, mode_attribute)
    return course_mode or 'verified'


def ls_eq(a: LSLike, b: LSLike) -> bool:
    if a is None or b is None:
        return False
    return dict(a) == dict(b)


def un_ls(string_dict: LSLike, preferred_lang: Optional[str] = None):
    """
    Take a LocalizedString or similar dict and try to determine the best to display to the user.

    If logging please set preferred_lang to 'en'.
    If able, you can provide the user's code as preferred_lang and it will be preferred over defaults.

    Args:
        preferred_lang (str): String value specifying linguistic and regional preferences using the IETF language tag
        format, as described in BCP 47.
        string_dict (dict|CTLocalizedString): a LocalizedString like value
    """
    if string_dict is None:
        return None

    preferred_langs = [*LS_OUT_PREFERENCES]

    if preferred_lang:
        preferred_langs = [preferred_lang, *preferred_langs]

    langs_available = list(string_dict.keys())
    length = len(langs_available)

    if length == 0:
        return None
    elif length == 1:
        return string_dict[langs_available[-1]]
    else:
        for lang in preferred_langs:
            if lang in langs_available:
                return string_dict[lang]

        # We didn't find anything, lets just pick the first. Sorry.
        return string_dict[langs_available[0]]


def price_to_string(price: CTPrice, money_as_decimal_string=False) -> str:
    """
    Convert Commercetools price to a string.

    This only relies on its underlying TypedMoney representation

    Args:
        price (CTPrice): Price value
        money_as_decimal_string (bool, optional): Should all money be returned as a decimal?

    Returns:
        string: A string representation

    """
    return typed_money_to_string(price.value, money_as_decimal_string)


def typed_money_to_string(money: CTTypedMoney, money_as_decimal_string=False) -> str:
    """
    Convert Commercetools typed money to a string.

    Args:
        money (TypedMoney): The value of meny to be stringified in its native locale.
        money_as_decimal_string (bool, optional): Should all money be returned as a decimal?

    Returns:
        string: A string representation

    """
    cur = Currency(money.currency_code)

    def _format(cost):
        if money_as_decimal_string:  # pragma no cover
            # This is used to support legacy ecomm mfe
            return str(cost)

        if money.currency_code in HIDE_CODE_FOR_CURRENCIES:
            return cur.get_money_format(cost)

        return cur.get_money_with_currency_format(cost)

    total = 0

    if isinstance(money, CTCentPrecisionMoney) or money.type == CTMoneyType.CENT_PRECISION:
        total = money.cent_amount
    elif isinstance(money, CTHighPrecisionMoney):  # pragma: no cover
        total = money.precise_amount

    if money.fraction_digits == 0:
        # this is likely Yen, but also cant DIV/0
        return _format(total)
    else:
        return _format(total / pow(10, money.fraction_digits))


def _typed_money_op(a: CTTypedMoney, b: Optional[CTTypedMoney], op):
    if b is None:  # pragma: no cover
        return a
    if (
        a.type == b.type and a.currency_code == b.currency_code and
        a.fraction_digits == b.fraction_digits
    ):
        if isinstance(a, CTHighPrecisionMoney):
            # noinspection PyUnresolvedReferences
            return CTHighPrecisionMoney(
                currency_code=a.currency_code,
                fraction_digits=a.fraction_digits,
                cent_amount=a.cent_amount,
                precise_amount=op(a.precise_amount, b.precise_amount)
            )
        return CTCentPrecisionMoney(
            currency_code=a.currency_code,
            fraction_digits=a.fraction_digits,
            cent_amount=op(a.cent_amount, b.cent_amount),
        )

    raise ValueError("This utility cannot convert between currencies, fractional digits nor TypedMoney types.")


def typed_money_add(a: CTTypedMoney, b: Optional[CTTypedMoney]):
    return _typed_money_op(a, b, lambda aint, bint: aint + bint)


def attribute_dict(attr_list: Optional[List[CTAttribute]]) -> Optional[dict]:
    if attr_list is None:
        return None
    if len(attr_list) >= 1:
        return dict([(d.name, d.value) for d in attr_list])
    return None


def get_line_item_bundle_id(line_item):
    """
    Retrieve the bundle ID from a line item's custom fields.
    Args:
        line_item (object): The line item object which contains custom fields.
    Returns:
        str or None: The bundle ID if it exists, otherwise None.
    """
    return (
            line_item.custom.fields.get(TwoUKeys.LINE_ITEM_BUNDLE_ID)
            if line_item.custom
            else None
        )


def check_is_bundle(line_items):
    """
    Checks if any of the line items in the provided list is part of a bundle.
    Args:
        line_items (list): A list of line items to check.
    Returns:
        bool: True if at least one line item is part of a bundle, False otherwise.
    """
    return any(bool(get_line_item_bundle_id(line_item)) for line_item in line_items)
