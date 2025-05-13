"""
Utils for the InAppPurchase app
"""

import logging
from typing import Optional

from commercetools.platform.models import Attribute, CentPrecisionMoney, Customer, LineItem

from commerce_coordinator.apps.commercetools.catalog_info.constants import EdXFieldNames
from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient
from commerce_coordinator.apps.commercetools.http_api_client import CTCustomAPIClient

logger = logging.getLogger(__name__)


def _get_attributes_to_update(
    *,
    user,
    customer: Customer,
    first_name: str,
    last_name: str,
) -> dict[str, str | None]:
    """
    Get the attributes that need to be updated for the customer.

    Args:
        customer: The existing customer object
        user: The authenticated user from the request

    Returns:
        A dictionary of attributes to update with their new values
    """
    updates = {}

    ct_lms_username = None
    if customer.custom and customer.custom.fields:
        ct_lms_username = customer.custom.fields.get(EdXFieldNames.LMS_USER_NAME)

    if ct_lms_username != user.username:
        updates["lms_username"] = user.username

    if customer.email != user.email:
        updates["email"] = user.email

    if customer.first_name != first_name:
        updates["first_name"] = first_name

    if customer.last_name != last_name:
        updates["last_name"] = last_name

    return updates


def get_email_domain(email: str | None) -> str:
    """Extract the domain from an email address.

    Args:
        email (str): Email address.

    Returns:
        Domain part of the email address.
    """
    return (email or "").lower().strip().partition("@")[-1]


def get_ct_customer(client: CommercetoolsAPIClient, user) -> Customer:
    """
    Get an existing customer for the authenticated user or create a new one.

    Args:
        client: CommercetoolsAPIClient instance
        user: The authenticated user from the request

    Returns:
        The customer object
    """
    customer = client.get_customer_by_lms_user_id(user.lms_user_id)
    first_name, last_name = user.first_name, user.last_name

    if not (first_name and last_name) and user.full_name:
        splitted_name = user.full_name.split(" ", 1)
        first_name = splitted_name[0]
        last_name = splitted_name[1] if len(splitted_name) > 1 else ""

    if customer:
        updates = _get_attributes_to_update(
            user=user,
            customer=customer,
            first_name=first_name,
            last_name=last_name,
        )
        if updates:
            customer = client.update_customer(
                customer=customer,
                updates=updates,
            )
    else:
        customer = client.create_customer(
            email=user.email,
            first_name=first_name,
            last_name=last_name,
            lms_user_id=user.lms_user_id,
            lms_username=user.username,
        )

    return customer


def get_standalone_price_for_sku(sku: str) -> CentPrecisionMoney:
    """
    Get the standalone price for a given SKU.

    Args:
        client: CommercetoolsAPIClient instance
        sku: The SKU of the product

    Returns:
        The standalone price
    """
    api_client = CTCustomAPIClient()

    response = api_client.get_standalone_prices_for_skus([sku])
    if not response or not response[0]:
        message = f"No standalone price found for the SKU: {sku}"
        logger.error(message)
        raise ValueError(message)

    try:
        value = response[0]["value"]
        return CentPrecisionMoney(
            cent_amount=value["centAmount"],
            currency_code=value["currencyCode"],
            fraction_digits=value["fractionDigits"]
        )
    except KeyError as exc:
        message = (
            f"No standalone price found for the SKU: {sku}, received: {response[0]}"
        )
        logger.exception(message, exc_info=exc)
        raise ValueError(message) from exc


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


def cents_to_dollars(amount: CentPrecisionMoney) -> float:
    """
    Get converted amount in dollars from cents upto fraction digits in points.

    Args:
       amount: dict (centAmount, fractionDigits, currencyCode)

    Returns:
        The converted amount in dollars
    """

    if not amount:
        return None

    cent_amount = amount.cent_amount or 0
    fraction_digits = amount.fraction_digits or 2

    return cent_amount / (10 ** fraction_digits)


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


def get_product_from_line_item(line_item: LineItem, standalone_price: CentPrecisionMoney) -> dict[str, any]:

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
