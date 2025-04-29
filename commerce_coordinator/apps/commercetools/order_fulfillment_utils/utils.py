import logging
from datetime import datetime

from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient
from commerce_coordinator.apps.core.constants import ISO_8601_FORMAT

logger = logging.getLogger(__name__)


def get_ct_order_and_customer(tag, order_id, message_id):
    """
    Retrieve order and customer information from CommercetoolsAPIClient
    for order fulfillment task.
    """
    client = CommercetoolsAPIClient()

    try:
        start_time = datetime.now()
        order = client.get_order_by_id(order_id)
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"[Performance Check] get_order_by_id call took {duration} seconds")
    except Exception as err:  # pragma no cover
        logger.error(f'[CT-{tag}] Order not found: {order_id} with CT error {err}, '
                     f'message id: {message_id}')
        raise

    try:
        customer = client.get_customer_by_id(order.customer_id)
    except Exception as err:  # pragma no cover
        logger.error(f'[CT-{tag}] Customer not found: {order.customer_id} for order {order_id} with '
                     f'CT error {err}, message id: {message_id}')
        raise

    return order, customer


def prepare_default_params(order, lms_user_id, source_system):
    """
    Prepare default parameters for order fulfillment task
    """
    return {
        'email_opt_in': True,
        'order_number': order.order_number,
        'order_id': order.id,
        'provider_id': None,
        'edx_lms_user_id': lms_user_id,
        'date_placed': order.last_modified_at.strftime(ISO_8601_FORMAT),
        'source_system': source_system,
    }
