import logging
from commercetools import CommercetoolsError
from .clients import CommercetoolsAPIClient

logger = logging.getLogger(__name__)

def update_line_item_state_on_fulfillment_completion(
        order_id,
        order_version,
        item_id,
        item_quantity,
        from_state_id,
        to_state_key
    ):
    client = CommercetoolsAPIClient()
    try:
        updated_order = client.update_line_item_transition_state_on_fulfillment(
            order_id,
            order_version,
            item_id,
            item_quantity,
            from_state_id,
            to_state_key
        )
        return updated_order
    except CommercetoolsError as err:
        logger.error(f"Unable to update line item [ {item_id} ] state on fulfillment "
                     f"success with error {err.errors} and correlation id {err.correlation_id}")
        return None
