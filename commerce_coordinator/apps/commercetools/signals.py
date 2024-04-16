"""
Commercetools signals and receivers.
"""
import logging

from commerce_coordinator.apps.commercetools.catalog_info.constants import TwoUKeys
from commerce_coordinator.apps.commercetools.tasks import update_line_item_state_on_fulfillment_completion
from commerce_coordinator.apps.core.signal_helpers import CoordinatorSignal, log_receiver

logger = logging.getLogger(__name__)

fulfill_order_placed_signal = CoordinatorSignal()


@log_receiver(logger)
def fulfill_order_completed_send_line_item_state(**kwargs):
    """
    Fulfill the order placed in Titan with a Celery task to LMS to enroll a user in a single course.
    """

    is_fulfilled = kwargs['is_fulfilled']

    if is_fulfilled:
        to_state_key = TwoUKeys.SUCCESS_FULFILMENT_STATE
    else:
        to_state_key = TwoUKeys.FAILURE_FULFILMENT_STATE

    result = update_line_item_state_on_fulfillment_completion(
        order_id=kwargs['order_id'],
        order_version=kwargs['order_version'],
        line_item_id=kwargs['line_item_id'],
        item_quantity=kwargs['item_quantity'],
        from_state_id=kwargs['line_item_state_id'],
        to_state_key=to_state_key
    )

    return result
