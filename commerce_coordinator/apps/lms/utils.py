"""LMS Utility Functions"""

from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient


def get_line_item_from_entitlement(order_number: str, entitlement_id: str) -> tuple[str, str]:
    """
    Retrieve the order ID and line item ID associated with the given entitlement ID.

    Args:
        order_number (str): The order number in Commercetools.
        entitlement_id (str): The entitlement ID to search for.

    Returns:
        tuple[str, str]: A tuple containing the order ID and the matching line item ID (if found,
        otherwise an empty string).
    """
    ct_api_client = CommercetoolsAPIClient()
    ct_order = ct_api_client.get_order_by_number(order_number=order_number)

    order_id = ct_order.id
    order_line_item_id = ''
    for line_item in ct_order.line_items:
        if line_item.custom.fields.get('edxLMSEntitlementId', '') == entitlement_id:
            order_line_item_id = line_item.id
            break

    return order_id, order_line_item_id
