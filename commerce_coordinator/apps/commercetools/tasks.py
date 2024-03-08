import logging
from commerce_coordinator.apps.commercetools.catalog_info.constants import TwoUKeys
from commercetools import CommercetoolsError
from .clients import CommercetoolsAPIClient

logger = logging.getLogger(__name__)

def update_line_item_state_on_fulfillment_success(
        order_id,
        order_version,
        item_id,
        item_quantity,
        from_state_id
    ):
    client = CommercetoolsAPIClient()  # Initialize your Commercetools client here
    try:
        # Update line item state for fulfillment success
        updated_order = client.update_line_item_transition_state_on_fulfillment(
            order_id,
            order_version,
            item_id,
            item_quantity,
            from_state_id,
            TwoUKeys.SUCCESS_FULFILMENT_STATE
        )
        return updated_order
    except CommercetoolsError as err:
        logger.error(f"Unable to update line item [ {item_id} ] state on fulfillment success with error {err.errors} and correlation id {err.correlation_id}")
        return None

# @shared_task
# def update_line_item_state_on_fulfillment_failure(order_id, order_version, item):
#     client = YourCommercetoolsClient()  # Initialize your Commercetools client here
#     try:
#         # Update line item state for fulfillment failure
#         updated_order = client.update_line_item_transition_state_on_fulfillment(order_id, order_version, item, from_state_id, "Fulfillment Failure")
#         return updated_order
#     except Exception as e:
#         logger.error(f"Error updating line item state on fulfillment failure: {str(e)}")
#         return None
