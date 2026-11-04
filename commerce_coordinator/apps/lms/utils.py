"""LMS Utility Functions"""

import re
from typing import List
from urllib.parse import urlencode

from django.conf import settings
from django.core.cache import cache
from requests.exceptions import RequestException

from commerce_coordinator.apps.commercetools.catalog_info.constants import TwoUKeys
from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient
from commerce_coordinator.apps.lms.clients import DiscoveryAPIClient
from commerce_coordinator.apps.lms.constants import (
    ALACARTE_COURSE_UUID_CACHE_TIMEOUT,
    CT_ABSOLUTE_DISCOUNT_TYPE,
    DEFAULT_BUNDLE_DISCOUNT_KEY
)
from commerce_coordinator.apps.rollout.utils import is_course_run_key
from commerce_coordinator.apps.rollout.waffle import is_redirect_to_alacarte_enabled_for_user


def get_order_line_item_info_from_entitlement_uuid(order_number: str, entitlement_uuid: str) -> tuple[str, str]:
    """
    Retrieve the order ID and line item ID associated with the given entitlement ID.

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
        bundle_ids_from_predicate = extract_uuids_from_predicate(cart_discount.get("cartPredicate", ""))

        if cart_discount_key == DEFAULT_BUNDLE_DISCOUNT_KEY:
            default_program_offer = cart_discount
        # Check if the offer is applied on the program except the default 10% offer
        elif bundle_key in bundle_ids_from_predicate:
            program_offer = cart_discount
            break

    # If no offer is applied on the program, check if it is also excluded from default 10% offer
    if not program_offer and default_program_offer:
        cart_predicate = default_program_offer.get("cartPredicate", "")
        excluded_bundle_ids_for_default_discount = extract_uuids_from_predicate(cart_predicate)

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


def get_course_uuid(course_run_key: str) -> str | None:
    """
    Get the UUID of the course of a course run from Discovery, or None when Discovery cannot tell.

    A course run never changes its course, so a UUID that was found is cached.
    """
    cache_key = f'alacarte.course_uuid.{course_run_key}'
    course_uuid = cache.get(cache_key)
    if course_uuid:
        return course_uuid

    try:
        course_uuid = DiscoveryAPIClient().get_course_uuid(course_run_key)
    except RequestException:
        return None  # the client has logged it

    if course_uuid:
        cache.set(cache_key, course_uuid, ALACARTE_COURSE_UUID_CACHE_TIMEOUT)
    return course_uuid


def get_alacarte_checkout_url(request) -> str | None:
    """
    Get the URL of the a la carte checkout for the purchase of one course, or None to keep today's checkout.

    The purchase goes to the a la carte checkout when the waffle flag is on for the user, and the link has one
    course run key and no bundle (program) or catalog (enterprise). The checkout needs the course UUID as well.
    """
    if not is_redirect_to_alacarte_enabled_for_user(request):
        return None

    query_params = request.GET
    course_run_keys = query_params.getlist('course_run_key')
    if len(course_run_keys) != 1 or query_params.get('bundle') or query_params.get('catalog'):
        return None

    course_run_key = course_run_keys[0].strip()
    if not is_course_run_key(course_run_key):
        return None

    course_uuid = get_course_uuid(course_run_key)
    if not course_uuid:
        return None

    query = urlencode({'course_uuid': course_uuid, 'course_run_key': course_run_key})
    return f'{settings.ALACARTE_CHECKOUT_URL}?{query}'
