"""
commercetools signals and receivers.
"""
import logging
from commerce_coordinator.apps.core.signal_helpers import CoordinatorSignal, log_receiver
from commerce_coordinator.apps.commercetools.tasks import update_line_item_state_on_fulfillment_success

logger = logging.getLogger(__name__)

fulfill_order_placed_signal = CoordinatorSignal()
# fulfillment_completed_signal = CoordinatorSignal()

@log_receiver(logger)
def fulfill_order_completed_send_line_item_state(**kwargs):
    """
    Fulfill the order placed in Titan with a Celery task to LMS to enroll a user in a single course.
    """
    # response_status = kwargs['response_status']  # Get the response code from kwargs
    item_state_ids = kwargs['state_ids']
    logger.info(f'-- ITEM STATES {item_state_ids}')
    result = None
    for item_state_id in item_state_ids:
            logger.info(f'-- STATE {item_state_id}')
            update_line_item_state_on_fulfillment_success(
                order_id=kwargs['order_id'],
                order_version=kwargs['order_version'],
                item_id=kwargs['item_id'],
                item_quantity=kwargs['item_quantity'],
                from_state_id=item_state_id,
            )
    # Depending on the response code, call the appropriate method
    # if response_status // 100 == 2:  # 2xx codes indicate success
    #     for item_state_id in item_state_ids:
    #             update_line_item_state_on_fulfillment_success(
    #                 order_id=kwargs['order_id'],
    #                 order_version=kwargs['order_version'],
    #                 item_id=kwargs['item_id'],
    #                 item_quantity=kwargs['item_quantity'],
    #                 from_state_id=item_state_id,
    #             )
    # else:
    #     print('In else')
        # fulfill_order_completed_send_line_item_state_failure(**kwargs)
    return result
