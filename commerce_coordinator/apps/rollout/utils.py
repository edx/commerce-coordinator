""" Rollout Utility Functions"""

import re
from typing import List

from commercetools.platform.models import Order as CTOrder
from commercetools.platform.models import ReturnItem as CTReturnItem
from commercetools.platform.models import ReturnPaymentState


def is_legacy_order(order_number: str) -> bool:
    """ Determine if an order is a Legacy Ecommerce order """
    if not order_number:
        return False
    return re.search("EDX-[0-9]{1,6}", order_number) is not None


def is_uuid(value: str) -> bool:
    """ Determine if an value is a UUID """
    if not value:
        return False
    return re.search(r"\b[A-Fa-f0-9]{8}(?:-[A-Fa-f0-9]{4}){3}-[A-Fa-f0-9]{12}\b", value) is not None


def get_order_return_info_return_items(order: CTOrder) -> List[CTReturnItem]:
    """ Returns array of Commercetools order return items """
    return_info_items = []
    for item in map(lambda x: x.items, order.return_info):
        return_info_items.extend(item)

    return return_info_items


def is_commercetools_line_item_already_refunded(
    order: CTOrder,
    order_line_item_id: str,
    return_info_return_items=None
) -> bool:
    """
    Checks if a given commercetools line item has already been refunded.
    Args:
        order (CTOrder): The commercetools order object. If not provided, it will be fetched using the order object.
        order_line_item_id (str): The ID of the order line item to check.
        return_info_return_items (list): A list of return items containing information about returned line items.
    Returns:
        bool: True if the line item has already been refunded, False otherwise.
    """
    return_info_return_items = get_order_return_info_return_items(order) if not return_info_return_items else \
        return_info_return_items
    return next(
        (
            item.line_item_id for item in return_info_return_items if item.line_item_id == order_line_item_id
            and item.payment_state == ReturnPaymentState.REFUNDED
        ), None
    )


def is_commercetools_stripe_refund(source_system: str) -> bool:
    """
    Determine if a refund made in Stripe dashboard is for a commercetools order based on event metadata
    """
    if not source_system:
        return False
    return source_system == 'commercetools'
