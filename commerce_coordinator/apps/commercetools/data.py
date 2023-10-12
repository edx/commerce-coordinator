from typing import Optional

from commercetools.platform.models import Address as CTAddress
from commercetools.platform.models import Customer as CTCustomer
from commercetools.platform.models import DirectDiscount as CTDirectDiscount
from commercetools.platform.models import DiscountCodeInfo as CTDiscountCodeInfo
from commercetools.platform.models import LineItem as CTLineItem
from commercetools.platform.models import Order as CTOrder

from commerce_coordinator.apps.commercetools.catalog_info.utils import price_to_string, un_ls
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
        username=customer.email  # pending response from CT, see: https://tinyurl.com/ykpwhbxt
    )


def order_from_commercetools(order: CTOrder) -> LegacyOrder:
    print(order)
    return LegacyOrder(

    )
