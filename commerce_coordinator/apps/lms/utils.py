"""LMS Utility Functions"""

from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient


def get_line_item_from_entitlement(order_number: str, entitlement_id: str) -> str:
    """
    Check if line item with given entitlement is present.
    """
    ct_api_client = CommercetoolsAPIClient()
    ct_order = ct_api_client.get_order_by_number(order_number=order_number)

    order_id = ct_order.id
    order_line_item_id = ''
    for line_item in ct_order.line_items:
        if line_item.custom.fields.get('edxLMSEntitlementId', '') == entitlement_id:
            order_line_item_id = line_item.id

    return order_id, order_line_item_id
