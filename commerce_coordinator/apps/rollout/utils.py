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


def is_commercetools_line_item_already_refunded(order: CTOrder, order_line_item_id: str) -> bool:
    """
    Determine if a return already exists for the Commercetools line item
    to prevent duplicate refunds/returns.
    """

    return_info_return_items = get_order_return_info_return_items(order)

    return len(list(filter(
        # Please verify the newly added check in which we are checking payment_state as well
        lambda item: item.line_item_id == order_line_item_id and item.payment_state == ReturnPaymentState.REFUNDED,
        return_info_return_items
    ))) >= 1

def is_commercetools_stripe_refund(source_system: str) -> bool:
    """
    Determine if a refund made in Stripe dashboard is for a commercetools order based on event metadata
    """
    if not source_system:
        return False
    return source_system == 'commercetools'
