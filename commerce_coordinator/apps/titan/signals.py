"""
Titan app signals and receivers.
"""

import logging

from commerce_coordinator.apps.core.signal_helpers import CoordinatorSignal, log_receiver
from commerce_coordinator.apps.titan.tasks import (
    enrollment_code_redemption_requested_create_order_task,
    order_created_save_task
)

logger = logging.getLogger(__name__)

fulfill_order_placed_signal = CoordinatorSignal()


@log_receiver(logger)
def enrollment_code_redemption_requested_create_order(**kwargs):
    """
    Create an order using the requested enrollment code.
    """
    enrollment_code_redemption_requested_create_order_task.delay(
        kwargs['user_id'],
        kwargs['username'],
        kwargs['email'],
        kwargs['sku'],
        kwargs['coupon_code'],
    )


@log_receiver(logger)
def order_created_save(**kwargs):
    """
    Create an order.
    """
    order_created_save_task.delay(
        kwargs['product_sku'],
        kwargs['edx_lms_user_id'],
        kwargs['email'],
        kwargs['first_name'],
        kwargs['last_name'],
        kwargs['coupon_code'],
    )
