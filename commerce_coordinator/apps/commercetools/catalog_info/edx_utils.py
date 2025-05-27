import decimal
from typing import List, Optional, Union

from commercetools.platform.models import Attribute, CentPrecisionMoney
from commercetools.platform.models import Customer as CTCustomer
from commercetools.platform.models import LineItem as CTLineItem
from commercetools.platform.models import Order as CTOrder
from commercetools.platform.models import Payment as CTPayment
from commercetools.platform.models import Product as CTProduct
from commercetools.platform.models import ProductVariant as CTProductVariant
from commercetools.platform.models import TransactionType

from commerce_coordinator.apps.commercetools.catalog_info.constants import (
    PAYMENT_STATUS_INTERFACE_CODE_SUCCEEDED,
    EdXFieldNames,
    TwoUKeys
)


def get_edx_product_course_run_key(prodvar_or_li: Union[CTProductVariant, CTLineItem]) -> str:
    if isinstance(prodvar_or_li, CTProductVariant):
        return prodvar_or_li.sku
    else:
        return prodvar_or_li.variant.sku


def get_edx_product_course_key(prod_or_li: Union[CTProduct, CTLineItem]) -> str:
    if isinstance(prod_or_li, CTProduct):
        return prod_or_li.key
    else:
        return prod_or_li.product_key


def get_edx_items(order: CTOrder) -> List[CTLineItem]:
    return list(filter(lambda x: True, order.line_items))


def get_edx_line_item(line_items: List[CTLineItem], line_item_id: str) -> Optional[CTLineItem]:
    """
    Retrieve a specific line item from a list of line items by its ID.

    Args:
        line_items (List[CTLineItem]): A list of line items to search.
        line_item_id (str): The ID of the line item to retrieve.

    Returns:
        CTLineItem or None: The line item with the matching ID, or None if not found.
    """
    return next(filter(lambda line_item: line_item.id == line_item_id, line_items), None)


def get_edx_line_item_state(line_item: CTLineItem) -> str:
    """
    Retrieve the state ID of the first state associated with a given line item.

    Args:
        line_item (CTLineItem): The line item object containing state information.

    Returns:
        str: The ID of the first state associated with the line item.
    """
    return line_item.state[0].state.id


def is_edx_lms_order(order: CTOrder) -> bool:
    return len(get_edx_items(order)) >= 1


def get_edx_lms_user_id(customer: CTCustomer):
    return customer.custom.fields[EdXFieldNames.LMS_USER_ID]


def get_edx_lms_user_name(customer: CTCustomer):
    return customer.custom.fields[EdXFieldNames.LMS_USER_NAME]


def get_edx_successful_payment_info(order: CTOrder):
    if not order.payment_info:
        return None, None
    for pr in order.payment_info.payments:
        pmt = pr.obj
        if pmt.payment_status.interface_code == PAYMENT_STATUS_INTERFACE_CODE_SUCCEEDED and pmt.interface_id:
            ct_payment_provider_id = pmt.payment_method_info.payment_interface
            return pmt, ct_payment_provider_id
    return None, None


def get_edx_psp_payment_id(order: CTOrder) -> Union[str, None]:
    """
    Retrieve the payment service provider (PSP) payment ID from an order.
    Currently supports:
        - Stripe: Payment Intent ID ("stripe_payment_intent_id")
        - PayPal: Order ID ("paypal_order_id")
    """
    pmt, _ = get_edx_successful_payment_info(order)
    if pmt:
        return pmt.interface_id
    return None


def get_edx_order_workflow_state_key(order: CTOrder) -> Optional[str]:
    order_workflow_state = None
    if order.state and order.state.obj:  # it should never be that we have one and not the other. # pragma no cover
        order_workflow_state = order.state.obj.key
    return order_workflow_state


def get_edx_is_sanctioned(order: CTOrder) -> bool:
    return get_edx_order_workflow_state_key(order) == TwoUKeys.SDN_SANCTIONED_ORDER_STATE


def cents_to_dollars(in_amount):

    if not in_amount:
        return None
    else:
        return in_amount.cent_amount / pow(
            10, in_amount.fraction_digits
            if hasattr(in_amount, 'fraction_digits')
            else 2
        )


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


def get_line_item_price_to_refund(order: CTOrder, return_line_item_ids: List[str]):
    """
    Calculate the discounted price of a line item in an order.

    Args:
        order (CTOrder): The order object containing line items.
        return_line_item_ids (List[str]): A list of line item IDs to check for discounted prices.

    Returns:
        decimal.Decimal: The discounted price of the line item in dollars. Returns 0.00 if no discounted price is found.
    """
    if check_is_bundle(order.line_items):
        bundle_amount = 0
        for line_item in get_edx_items(order):
            if line_item.id in return_line_item_ids:
                bundle_amount += cents_to_dollars(line_item.total_price)

        return bundle_amount

    return cents_to_dollars(order.total_price)


def get_edx_refund_info(payment: CTPayment, order: CTOrder, return_line_item_ids: List[str]) -> (decimal.Decimal, str):
    """
    Calculate the refund amount for specified line items in an order and retrieve the interaction ID from the payment.

    Args:
        payment (CTPayment): The payment object containing transaction details.
        order (CTOrder): The order object containing line items and pricing details.
        return_line_item_ids (List[str]): A list of line item IDs for which the refund is to be calculated.

    Returns:
        tuple: A tuple containing:
            - decimal.Decimal: The total refund amount for the specified line items.
            - str: The interaction ID associated with the charge transaction in the payment.
    """
    interaction_id = None

    for transaction in payment.transactions:
        if transaction.type == TransactionType.CHARGE:  # pragma no cover
            interaction_id = transaction.interaction_id

    refund_amount = get_line_item_price_to_refund(order, return_line_item_ids)

    return refund_amount, interaction_id


def get_line_item_lms_entitlement_id(line_item):
    """
    Retrieve the lms entitlement ID from a line item's custom fields.
    Args:
        line_item (object): The line item object which contains custom fields.
    Returns:
        str or None: The lms entitlement ID if it exists, otherwise None.
    """
    return (
            line_item.custom.fields.get(TwoUKeys.LINE_ITEM_LMS_ENTITLEMENT_ID)
            if line_item.custom
            else None
        )


def sum_money(*args: Optional[list[CentPrecisionMoney]]) -> CentPrecisionMoney:

    """
    Sums multiple CentPrecisionMoney objects.

    Args:
        *args: Variable number of CentPrecisionMoney dictionaries or None.

    Returns:
        A CentPrecisionMoney object with the total centAmount,
        using the fractionDigits and currencyCode from the first valid entry.
        Returns None if no valid money object is provided.
    """

    amount_list = [amount for amount in args if amount]

    if not amount_list:
        return None

    total_cent_amount = sum(amount.cent_amount for amount in amount_list)

    return {
        'cent_amount': total_cent_amount,
        'fraction_digits': amount_list[0].fraction_digits,
        'currency_code': amount_list[0].currency_code
    }


def get_attribute_value(attributes: list[Attribute], key: str):

    """
    Returns the value of an attribute matching the provided key.

    Args:
        attributes (List[Attribute]): List of product variant attributes.
        key (str): Name of the attribute to find.

    Returns:
        The value of the matching attribute, or None if not found.
    """
    for attr in attributes:
        if attr.name == key:
            return attr.value
    return None


def get_product_from_line_item(line_item: CTLineItem, standalone_price: CentPrecisionMoney) -> dict[str, any]:

    """
    Extracts and formats product information from a line item.

    Args:
        line_item (LineItem): The line item containing product and variant details.
        standalone_price (CentPrecisionMoney): The price of the product in cent precision format.

    Returns:
        dict[str, any]: A dictionary representing the product with keys such as:
            - product_id (str or None): The course key or product key depending on product type.
            - sku (str): SKU of the product variant.
            - name (LocalizedString): Localized name of the product.
            - price (float): Price converted to dollars.
            - quantity (int): Quantity of the item in the line.
            - category (str or None): Primary subject area if present in attributes.
            - url (str or None): Course URL if present in attributes.
            - lob (str): Line of business; defaults to "edx".
            - image_url (str or None): First image URL from variant if available.
            - brand (str or None): Brand name from attributes.
            - product_type (str or None): Name of the product type.
    """

    product_key = line_item.product_key
    name = line_item.name
    product_type = line_item.product_type
    count = line_item.quantity
    variant = line_item.variant
    attributes = variant.attributes
    images = variant.images
    product_id = None

    if product_type and product_type.obj.key == "edx_course_entitlement":
        for attr in variant["attributes"]:
            if attr["name"] == "course-key":
                product_id = attr["value"]
                break
    else:
        product_id = product_key

    return {
        "product_id": product_id,
        "sku": variant.sku,
        "name": name,
        "price": cents_to_dollars(standalone_price),
        "quantity": count,
        "category": get_attribute_value(attributes, "primary-subject-area"),
        "url": get_attribute_value(attributes, "url-course"),
        "lob": get_attribute_value(attributes, "lob") or "edx",
        "image_url": images[0] if images else None,
        "brand": get_attribute_value(attributes, "brand-text"),
        "product_type": product_type.obj.name if product_type.obj.name else None,
    }
