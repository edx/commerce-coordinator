from typing import Optional

from commercetools.platform.models import Address as CTAddress
from commercetools.platform.models import Customer as CTCustomer
from commercetools.platform.models import DirectDiscount as CTDirectDiscount
from commercetools.platform.models import DiscountCodeInfo as CTDiscountCodeInfo
from commercetools.platform.models import LineItem as CTLineItem
from commercetools.platform.models import Order as CTOrder

from commerce_coordinator.apps.commercetools.catalog_info.constants import EdXFieldNames
from commerce_coordinator.apps.commercetools.catalog_info.utils import price_to_string, typed_money_to_string, un_ls
from commerce_coordinator.apps.ecommerce.data import BillingAddress, Line
from commerce_coordinator.apps.ecommerce.data import Order as LegacyOrder
from commerce_coordinator.apps.ecommerce.data import User, Voucher


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


def convert_line_item(li: CTLineItem) -> Line:
    return Line(
        title=un_ls(li.name),
        quantity=li.quantity,
        # TODO: course_organization=
        # TODO: description=
        # TODO: status=
        line_price_excl_tax=price_to_string(li.price),
        unit_price_excl_tax=price_to_string(li.price)
    )


def convert_discount_code_info(dci: Optional[CTDiscountCodeInfo]) -> Optional[Voucher]:
    print(dci)
    return None


def convert_direct_discount(dd: Optional[CTDirectDiscount]) -> Optional[Voucher]:
    print(dd)
    return None


def convert_customer(customer: CTCustomer) -> User:
    return User(
        email=customer.email,
        username=customer.custom.fields[EdXFieldNames.LMS_USER_NAME]
    )


def order_from_commercetools(order: CTOrder, customer: CTCustomer) -> LegacyOrder:
    print(order)
    return LegacyOrder(
        user=convert_customer(customer),
        lines=[convert_line_item(x) for x in order.line_items],
        billing_address=convert_address(order.billing_address),
        date_placed=order.completed_at.isoformat(),
        total_excl_tax=typed_money_to_string(order.total_price),
        # in dev systems, this isn't set... so let's use UUID, otherwise, lets rely on order number
        number=order.order_number or order.id,
        currency=order.total_price.currency_code,
        payment_processor="stripe via commercetools",
        status=order.order_state.CONFIRMED.value
        #payment_method=order.payment_info.payments[0].type_id
    )
