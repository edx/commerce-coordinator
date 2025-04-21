"""LMS Utility Functions"""

import re
from typing import List

from commerce_coordinator.apps.commercetools.catalog_info.constants import TwoUKeys
from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient
from commerce_coordinator.apps.lms.constants import CT_ABSOLUTE_DISCOUNT_TYPE, DEFAULT_BUNDLE_DISCOUNT_KEY


def get_order_line_item_info_from_entitlement_uuid(order_number: str, entitlement_uuid: str) -> tuple[str, str]:
    """
    Retrieve the order and line item ID's associated with the given entitlement ID.

    Args:
        order_number (str): The order number in Commercetools.
        entitlement_uuid (str): The entitlement ID to search for.

    Returns:
        tuple[str, str]: A tuple containing the order ID and the matching line item ID (if found,
        otherwise an empty string).
    """
    ct_api_client = CommercetoolsAPIClient()
    ct_order = ct_api_client.get_order_by_number(order_number=order_number)

    order_id = ct_order.id
    order_line_item_id = ''
    for line_item in ct_order.line_items:
        if line_item.custom.fields.get(TwoUKeys.LINE_ITEM_LMS_ENTITLEMENT_ID, '') == entitlement_uuid:
            order_line_item_id = line_item.id
            break

    return order_id, order_line_item_id


def extract_uuids_from_predicate(predicate: str) -> List[str]:
    """
    Extract program UUIDs from a predicate.

    Args:
        predicate (str): Predicate for the cart discount.

    Returns:
        list: List of program UUIDs.
    """
    return re.findall(r'custom\.bundleId\s*(?:!=|=)\s*"([^"]+)"', predicate)


def get_program_offer(cart_discounts: list, bundle_key: str) -> dict:
    """Get the discount offer applied on program."""

    program_offer = None
    default_program_offer = None
    for cart_discount in cart_discounts:
        cart_discount_key = cart_discount.get("key")
        bundle_ids_from_predicate = extract_uuids_from_predicate(cart_discount.get("target", {}).get("predicate"))

        if cart_discount_key == DEFAULT_BUNDLE_DISCOUNT_KEY:
            default_program_offer = cart_discount
        # Check if the offer is applied on the program except the default 10% offer
        elif bundle_key in bundle_ids_from_predicate:
            program_offer = cart_discount
            break

    # If no offer is applied on the program, check if it is also excluded from default 10% offer
    if not program_offer and default_program_offer:
        predicate = default_program_offer.get("target", {}).get("predicate")
        excluded_bundle_ids_for_default_discount = extract_uuids_from_predicate(predicate)

        if bundle_key in excluded_bundle_ids_for_default_discount:
            return None

    program_offer = program_offer or default_program_offer
    if not program_offer:
        return None

    discount_key = program_offer.get("key")
    discount_value = program_offer.get("value", {})
    discount_type = discount_value.get("type")

    # Extract discount value based on type
    if discount_type == CT_ABSOLUTE_DISCOUNT_TYPE:
        discount_value_in_cents = discount_value.get("money", [{}])[0].get("centAmount", 0)
    else:
        discount_value_in_cents = discount_value.get("permyriad", 0)

    return {
        "discount_value_in_cents": discount_value_in_cents,
        "discount_type": discount_type,
        "key": discount_key,
    }
