""" Rollout Utility Functions"""

import re


def is_legacy_order(order_number: str) -> bool:
    """ Determine if an order is a Legacy Ecommerce order """
    if not order_number:
        return False
    return re.search("EDX-[0-9]{1,6}", order_number) is not None


def is_uuid(value: str) -> bool:
    """ Determine if an value is a UUID """
    if not value:
        return False
    return re.search(r"\b[A-F0-9]{8}(?:-[A-F0-9]{4}){3}-[A-F0-9]{12}\b", value) is not None
