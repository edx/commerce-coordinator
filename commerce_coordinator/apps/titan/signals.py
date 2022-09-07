"""
Titan app signals and receivers.
"""

import logging

from commerce_coordinator.apps.core.signal_helpers import coordinator_receiver
from commerce_coordinator.apps.titan.tasks import (
    enrollment_code_redemption_requested_create_order_oauth_task,
    enrollment_code_redemption_requested_create_order_task
)

logger = logging.getLogger(__name__)


@coordinator_receiver(logger)
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
    enrollment_code_redemption_requested_create_order_oauth_task.delay(
        kwargs['user_id'],
        kwargs['username'],
        kwargs['email'],
        kwargs['sku'],
        kwargs['coupon_code'],
    )
