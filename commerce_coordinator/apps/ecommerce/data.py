from datetime import datetime
from typing import List, Optional

from attr.validators import and_, gt, instance_of, lt, max_len, min_len, optional
from attrs import field, frozen, mutable

# More Information:
#   https://open-edx-proposals.readthedocs.io/en/latest/best-practices/oep-0049-django-app-patterns.html#data-py

@mutable
class BillingAddress:
    """
    BillingAddress
    """
    first_name: Optional[str] = field(validator=optional([instance_of(str), max_len(255)]))
    last_name: Optional[str] = field(validator=optional([instance_of(str), max_len(255)]))
    line1: str = field(validator=and_([instance_of(str), max_len(255), min_len(1)]))
    line2: Optional[str] = field(validator=optional([instance_of(str), max_len(255)]))
    city: str = field(validator=optional([instance_of(str), max_len(255), min_len(1)]))
    state: Optional[str] = field(validator=optional([instance_of(str), max_len(255)]))
    postcode: Optional[str] = field(validator=optional([instance_of(str), max_len(64)]))
    country: str


@mutable
class Category:
    """
    Category
    """
    id: Optional[int]
    name: str = field(validator=optional([instance_of(str), max_len(255), min_len(1)]))


@mutable
class Coupon:
    """
    Coupon
    """
    benefit_type: Optional[str] = field(validator=optional(instance_of(str)))
    benefit_value: Optional[str] = field(validator=optional(instance_of(str)))
    catalog_query: Optional[str] = field(validator=optional(instance_of(str)))
    course_catalog: Optional[str] = field(validator=optional(instance_of(str)))
    category: Optional[str] = field(validator=optional(instance_of(str)))
    client: Optional[str] = field(validator=optional(instance_of(str)))
    code: Optional[str] = field(validator=optional(instance_of(str)))
    code_status: Optional[str] = field(validator=optional(instance_of(str)))
    coupon_type: Optional[str] = field(validator=optional(instance_of(str)))
    course_seat_types: Optional[str] = field(validator=optional(instance_of(str)))
    email_domains: Optional[str] = field(validator=optional(instance_of(str)))
    end_date: Optional[str] = field(validator=optional(instance_of(str)))
    enterprise_catalog_content_metadata_url: Optional[str] = field(validator=optional(instance_of(str)))
    enterprise_customer: Optional[str] = field(validator=optional(instance_of(str)))
    enterprise_customer_catalog: Optional[str] = field(validator=optional(instance_of(str)))
    id: Optional[int]
    inactive: Optional[str] = field(validator=optional(instance_of(str)))
    last_edited: Optional[str] = field(validator=optional(instance_of(str)))
    max_uses: Optional[str] = field(validator=optional(instance_of(str)))
    note: Optional[str] = field(validator=optional(instance_of(str)))
    notify_email: Optional[str] = field(validator=optional(instance_of(str)))
    num_uses: Optional[str] = field(validator=optional(instance_of(str)))
    payment_information: Optional[str] = field(validator=optional(instance_of(str)))
    program_uuid: Optional[str] = field(validator=optional(instance_of(str)))
    price: Optional[str] = field(validator=optional(instance_of(str)))
    quantity: Optional[str] = field(validator=optional(instance_of(str)))
    seats: Optional[str] = field(validator=optional(instance_of(str)))
    start_date: Optional[str] = field(validator=optional(instance_of(str)))
    title: Optional[str] = field(validator=optional([instance_of(str), max_len(255)]))
    voucher_type: Optional[str] = field(validator=optional(instance_of(str)))
    contract_discount_value: Optional[str] = field(validator=optional(instance_of(str)))
    contract_discount_type: Optional[str] = field(validator=optional(instance_of(str)))
    prepaid_invoice_amount: Optional[str] = field(validator=optional(instance_of(str)))
    sales_force_id: Optional[str] = field(validator=optional(instance_of(str)))


@mutable
class Line:
    """
    Line
    """
    title: str = field(validator=optional([instance_of(str), max_len(255), min_len(1)]))
    quantity: Optional[int] = field(validator=optional([instance_of(int), lt(4294967295), gt(0)]))
    line_price_excl_tax: str
    course_organization: Optional[str] = field(validator=optional(instance_of(str)))
    description: Optional[str] = field(validator=optional(instance_of(str)))
    status: Optional[str] = field(validator=optional([instance_of(str), max_len(255)]))
    unit_price_excl_tax: Optional[str] = field(validator=optional(instance_of(str)))


@mutable
class StockRecord:
    """
    StockRecord
    """
    id: Optional[int]
    product: int
    partner: int
    partner_sku: str = field(validator=and_([instance_of(str), max_len(128), min_len(1)]))
    price_currency: Optional[str] = field(validator=optional([instance_of(str), max_len(12), min_len(1)]))
    price_excl_tax: Optional[str] = field(validator=optional(instance_of(str)))


@mutable
class Product:
    """
    Product
    """
    id: Optional[int]
    url: Optional[str] = field(validator=optional(instance_of(str)))
    structure: Optional[str] = field(validator=optional(instance_of(str)))
    product_class: Optional[str] = field(validator=optional(instance_of(str)))
    title: Optional[str] = field(validator=optional([instance_of(str), max_len(255)]))
    price: Optional[str] = field(validator=optional(instance_of(str)))
    expires: Optional[datetime]
    attribute_values: Optional[str] = field(validator=optional(instance_of(str)))
    is_available_to_buy: Optional[str] = field(validator=optional(instance_of(str)))
    is_enrollment_code_product: Optional[str] = field(validator=optional(instance_of(str)))
    stockrecords: Optional[List[StockRecord]]


@mutable
class User:
    """
    User
    """
    username: str = field(validator=optional([instance_of(str), max_len(150), min_len(1)]))
    email: Optional[str] = field(validator=optional([instance_of(str), max_len(254)]))
    """Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."""


@mutable
class Voucher:
    """
    Voucher
    """
    id: Optional[int]
    start_datetime: datetime
    end_datetime: datetime
    offers: List[int]
    name: str = field(validator=optional([instance_of(str), max_len(128), min_len(1)]))
    """This will be shown in the checkout and basket once the coupon is entered"""
    code: str = field(validator=optional([instance_of(str), max_len(128), min_len(1)]))
    """Case insensitive / No spaces allowed"""
    redeem_url: Optional[str] = field(validator=optional(instance_of(str)))
    usage: Optional[str] = field(validator=optional(instance_of(str)))
    num_basket_additions: Optional[int] = field(validator=optional([instance_of(int), lt(4294967295), gt(0)]))
    num_orders: Optional[int] = field(validator=optional([instance_of(int), lt(4294967295), gt(0)]))
    total_discount: Optional[str] = field(validator=optional(instance_of(str)))
    date_created: Optional[datetime]
    is_available_to_user: Optional[str] = field(validator=optional(instance_of(str)))
    benefit: Optional[str] = field(validator=optional(instance_of(str)))
    is_public: Optional[bool]
    """Should this code batch be public or private for assignment."""


@mutable
class Order:
    """
    A validating Mutable Order
    """
    date_placed: datetime
    user: User
    total_excl_tax: str
    lines: List[Line]
    number: str = field(validator=optional([instance_of(str), max_len(128), min_len(1)]))

    basket_discounts: Optional[str] = field(validator=optional(instance_of(str)))
    billing_address: Optional[BillingAddress]
    contains_credit_seat: Optional[str] = field(validator=optional(instance_of(str)))
    currency: Optional[str] = field(validator=optional([instance_of(str), max_len(12), min_len(1)]))
    dashboard_url: Optional[str] = field(validator=optional(instance_of(str)))
    discount: Optional[str] = field(validator=optional(instance_of(str)))
    enable_hoist_order_history: Optional[str] = field(validator=optional(instance_of(str)))
    enterprise_learner_portal_url: Optional[str] = field(validator=optional(instance_of(str)))
    order_product_ids: Optional[str] = field(validator=optional(instance_of(str)))
    payment_processor: Optional[str] = field(validator=optional(instance_of(str)))
    payment_method: Optional[str] = field(validator=optional(instance_of(str)))
    product_tracking: Optional[str] = field(validator=optional(instance_of(str)))
    status: Optional[str] = field(validator=optional([instance_of(str), max_len(100)]))
    total_before_discounts_incl_tax: Optional[str] = field(validator=optional(instance_of(str)))
    vouchers: Optional[str] = field(validator=optional(instance_of(str)))


@frozen
class EcommerceOrder(Order):
    """ A Frozen Ecommerce Order """
    pass


"""
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "basket_discounts": [],
      "billing_address": {
        "first_name": "Glenn Martin",
        "last_name": "",
        "line1": "123 AnyStreet Ln",
        "line2": "",
        "postcode": "02000",
        "state": "MA",
        "country": "US",
        "city": "Norwood"
      },
      "contains_credit_seat": false,
      "currency": "USD",
      "date_placed": "2023-03-23T17:08:43Z",
      "dashboard_url": "https://theseusdemo.sandbox.edx.org/dashboard",
      "discount": "0",
      "enable_hoist_order_history": false,
      "enterprise_learner_portal_url": null,
      "lines": [
        {
          "title": "Seat in edX Demonstration Course with verified certificate",
          "quantity": 1,
          "course_organization": "edX",
          "description": "Seat in edX Demonstration Course with verified certificate",
          "status": "Complete",
          "line_price_excl_tax": "149.00",
          "unit_price_excl_tax": "149.00",
          "product": {
            "id": 3,
            "url": "https://ecommerce-theseusdemo.sandbox.edx.org/api/v2/products/3/",
            "structure": "child",
            "product_class": "Seat",
            "title": "Seat in edX Demonstration Course with verified certificate",
            "price": "149.00",
            "expires": "2024-03-13T14:12:05.024240Z",
            "attribute_values": [
              {
                "name": "certificate_type",
                "code": "certificate_type",
                "value": "verified"
              },
              {
                "name": "course_key",
                "code": "course_key",
                "value": "course-v1:edX+DemoX+Demo_Course"
              },
              {
                "name": "id_verification_required",
                "code": "id_verification_required",
                "value": true
              }
            ],
            "is_available_to_buy": true,
            "is_enrollment_code_product": false,
            "stockrecords": [
              {
                "id": 3,
                "product": 3,
                "partner": 1,
                "partner_sku": "8CF08E5",
                "price_currency": "USD",
                "price_excl_tax": "149.00"
              }
            ]
          }
        }
      ],
      "number": "EDX-100029",
      "order_product_ids": "3",
      "payment_processor": "stripe",
      "payment_method": "Visa 1111",
      "product_tracking": null,
      "status": "Complete",
      "total_before_discounts_incl_tax": "149.00",
      "total_excl_tax": "149.00",
      "user": {
        "email": "gmartin+glenn_6@2u.com",
        "username": "glenn_6"
      },
      "vouchers": []
    }
  ]
}
"""

"""

"""
