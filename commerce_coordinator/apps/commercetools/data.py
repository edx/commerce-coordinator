""" Conversion methods to convert a Commercetools order in to a Legacy Ecommerce one """

from typing import List, Optional

from commercetools.platform.models import Address as CTAddress
from commercetools.platform.models import Customer as CTCustomer
from commercetools.platform.models import DirectDiscount as CTDirectDiscount
from commercetools.platform.models import DiscountCodeInfo as CTDiscountCodeInfo
from commercetools.platform.models import LineItem as CTLineItem
from commercetools.platform.models import Order as CTOrder
from commercetools.platform.models import PaymentInfo as CTPaymentInfo
from django.conf import settings

from commerce_coordinator.apps.commercetools.catalog_info.constants import SEND_MONEY_AS_DECIMAL_STRING, EdXFieldNames
from commerce_coordinator.apps.commercetools.catalog_info.utils import (
    attribute_dict,
    get_line_item_attribute,
    price_to_string,
    typed_money_add,
    typed_money_to_string,
    un_ls
)
from commerce_coordinator.apps.commercetools.utils import calculate_total_discount_on_order
from commerce_coordinator.apps.ecommerce.data import BillingAddress, Line
from commerce_coordinator.apps.ecommerce.data import Order as LegacyOrder
from commerce_coordinator.apps.ecommerce.data import User


def this_or(a, b):
    return a if a else b


def convert_address(address: Optional[CTAddress]) -> Optional[BillingAddress]:
    if not address:
        return None

    return BillingAddress(
        first_name=address.first_name,
        last_name=address.last_name,
        line1=f"{address.street_number} {address.street_name}",
        line2=address.additional_street_info,
        postcode=address.postal_code,
        state=address.state,
        country=address.country,
        city=address.city
    )


def convert_line_item(li: CTLineItem, payment_state: str) -> Line:
    return Line(
        title=un_ls(li.name),
        quantity=li.quantity,
        course_organization=get_line_item_attribute(li, 'brand-text'),
        description=un_ls(li.name),
        status=payment_state,
        line_price_excl_tax=price_to_string(li.price, money_as_decimal_string=SEND_MONEY_AS_DECIMAL_STRING),
        unit_price_excl_tax=price_to_string(li.price, money_as_decimal_string=SEND_MONEY_AS_DECIMAL_STRING)
    )


def convert_line_item_prod_id(li: CTLineItem) -> str:
    """
    Convert a Commercetools Line Item to a String for Legacy Orders
    Args:
        li: Commercetools LineItem instance

    Returns: Our best guess at the product line items id.

    """
    key_name = 'courserun-id'  # this could be wrong and will likely change when the catalog is 'fixed'
    attrs = attribute_dict(li.variant.attributes)

    if attrs and key_name in attrs and attrs[key_name]:  # pragma no cover
        return this_or(attrs[key_name], li.product_id)
    return li.product_id


def convert_discount_code_info(dcis: Optional[List[CTDiscountCodeInfo]]) -> Optional[str]:
    if not dcis or len(dcis) < 1:
        return None
    return ", ".join([x.discount_code.obj.code for x in dcis])


def convert_direct_discount(dds: Optional[List[CTDirectDiscount]]) -> Optional[str]:
    if not dds or len(dds) < 1:
        return None
    # idk how to format this one. We may have to wait till we have an example.
    return ", ".join([x.value.type for x in dds])


def convert_customer(customer: CTCustomer) -> User:
    return User(
        email=customer.email,
        username=customer.custom.fields[EdXFieldNames.LMS_USER_NAME]
    )


def convert_payment_info(payment_info: CTPaymentInfo) -> str:
    if len(payment_info.payments) > 0:
        return un_ls(payment_info.payments[-1].obj.payment_method_info.name)
    return "Unknown"


def order_from_commercetools(order: CTOrder, customer: CTCustomer) -> LegacyOrder:
    payment_state = order.payment_state.value
    discounted_amount = calculate_total_discount_on_order(order)

    return LegacyOrder(
        user=convert_customer(customer),
        lines=[convert_line_item(x, payment_state) for x in order.line_items],
        billing_address=convert_address(order.billing_address),
        date_placed=order.last_modified_at,
        total_excl_tax=typed_money_to_string(order.total_price, money_as_decimal_string=SEND_MONEY_AS_DECIMAL_STRING),
        number=order.order_number,
        currency=order.total_price.currency_code,
        payment_processor="stripe via commercetools",
        status=order.order_state.CONFIRMED.value,
        dashboard_url=settings.LMS_DASHBOARD_URL,
        order_product_ids=", ".join([convert_line_item_prod_id(x) for x in order.line_items]),
        basket_discounts=convert_direct_discount(order.direct_discounts),
        contains_credit_seat="True",
        discount=typed_money_to_string(discounted_amount,
                                       money_as_decimal_string=SEND_MONEY_AS_DECIMAL_STRING)
        if order.discount_on_total_price else None,  # NYI
        enable_hoist_order_history="False",  # ?
        enterprise_learner_portal_url="about:blank",
        product_tracking=None,
        total_before_discounts_incl_tax=typed_money_to_string(
            typed_money_add(
                typed_money_add(
                    order.total_price,
                    discounted_amount if discounted_amount.cent_amount else None
                ),
                order.taxed_price.total_tax
            ),
            money_as_decimal_string=SEND_MONEY_AS_DECIMAL_STRING
        ),
        vouchers=this_or(
            convert_discount_code_info(order.discount_codes),
            convert_direct_discount(order.direct_discounts)
        ),
        payment_method=convert_payment_info(order.payment_info)
    )
