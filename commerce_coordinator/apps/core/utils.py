import re


def is_legacy_order(order_number: str) -> bool:
    """ Determine if an order is a Legacy Ecommerce order """
    if not order_number:
        return False
    if re.search("EDX-[0-9]{1,6}", order_number):
        return True
    else:
        return False


def is_uuid(value: str) -> bool:
    """ Determine if an value is a UUID """
    if not value:
        return False
    if re.search(r"\b[A-F0-9]{8}(?:-[A-F0-9]{4}){3}-[A-F0-9]{12}\b", value):
        return True
    else:
        return False


def generate_receipt_url(order_id_or_number: str):
    if is_legacy_order(order_id_or_number) or is_uuid(order_id_or_number):
        return "http:/XXXXX" + order_id_or_number
    else:
        raise ValueError("Invalid order id or number")
