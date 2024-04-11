"""
Commercetools Delayed Signal Receivers (to invoke Celery Tasks)
"""

import logging

from commerce_coordinator.apps.commercetools.sub_messages.tasks import (
    fulfill_order_placed_message_signal_task,
    fulfill_order_returned_signal_task,
    fulfill_order_sanctioned_message_signal_task
)
from commerce_coordinator.apps.core.signal_helpers import log_receiver

logger = logging.getLogger(__name__)


@log_receiver(logger)
def fulfill_order_placed_message_signal(**kwargs):
    """ CoordinatorSignal receiver to invoke Celery Task fulfill_order_placed_message_signal_task"""
    async_result = fulfill_order_placed_message_signal_task.delay(
        order_id=kwargs['order_id'],
        source_system=kwargs['source_system'],
    )
    return async_result.id


@log_receiver(logger)
def fulfill_order_sanctioned_message_signal(**kwargs):
    """ CoordinatorSignal receiver to invoke Celery Task fulfill_order_sanctioned_message_signal"""
    async_result = fulfill_order_sanctioned_message_signal_task.delay(
        order_id=kwargs['order_id'],
    )
    return async_result.id


@log_receiver(logger)
def fulfill_order_returned_signal(**kwargs):
    """ CoordinatorSignal receiver to invoke Celery Task fulfill_order_returned_signal"""
    async_result = fulfill_order_returned_signal_task.delay(
        order_id=kwargs['order_id'],
    )
    return async_result.id
