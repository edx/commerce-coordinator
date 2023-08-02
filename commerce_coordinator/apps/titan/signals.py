"""
Titan app signals and receivers.
"""

import logging

from commerce_coordinator.apps.core.signal_helpers import CoordinatorSignal, log_receiver
from commerce_coordinator.apps.titan.tasks import (
    enrollment_code_redemption_requested_create_order_task,
    order_created_save_task,
    payment_processed_save_task
)

logger = logging.getLogger(__name__)

fulfill_order_placed_signal = CoordinatorSignal()


@log_receiver(logger)
def enrollment_code_redemption_requested_create_order(**kwargs):
    """
    Create an order using the requested enrollment code.
    """
    async_result = enrollment_code_redemption_requested_create_order_task.delay(
        kwargs['user_id'],
        kwargs['username'],
        kwargs['email'],
        kwargs['sku'],
        kwargs['coupon_code'],
    )
    return async_result.id


@log_receiver(logger)
def order_created_save(**kwargs):
    """
    Create an order.
    """
    async_result = order_created_save_task.delay(
        kwargs['sku'],
        kwargs['edx_lms_user_id'],
        kwargs['email'],
        kwargs['coupon_code'],
    )
    return async_result.id


@log_receiver(logger)
def payment_processed_save(**kwargs):
    """
    Update an payment.
    """
    async_result = payment_processed_save_task.delay(
        kwargs['payment_number'],
        kwargs['payment_state'],
        kwargs['response_code'],
    )
    return async_result.id
