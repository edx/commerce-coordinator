"""
Commercetools signals and receivers.
"""

import logging

from commerce_coordinator.apps.commercetools.catalog_info.constants import TwoUKeys
from commerce_coordinator.apps.commercetools.tasks import (
    fulfillment_completed_update_ct_line_item_task,
    refund_from_paypal_task,
    refund_from_stripe_task
)
from commerce_coordinator.apps.core.signal_helpers import CoordinatorSignal, log_receiver

logger = logging.getLogger(__name__)

fulfill_order_placed_send_enroll_in_course_signal = CoordinatorSignal()
fulfill_order_placed_send_entitlement_signal = CoordinatorSignal()


@log_receiver(logger)
def fulfillment_completed_update_ct_line_item(**kwargs):
    """
   Update the line item of the order placed in Commercetools based on LMS entitlement
    """
    is_fulfilled = kwargs["is_fulfilled"]

    if is_fulfilled:
        to_state_key = TwoUKeys.SUCCESS_FULFILMENT_STATE
    else:
        to_state_key = TwoUKeys.FAILURE_FULFILMENT_STATE

    async_result = fulfillment_completed_update_ct_line_item_task.delay(
        entitlement_uuid=kwargs.get("entitlement_uuid", ""),
        order_id=kwargs["order_id"],
        line_item_id=kwargs["line_item_id"],
        to_state_key=to_state_key,
    )

    return async_result.id


@log_receiver(logger)
def refund_from_stripe(**kwargs):
    """
    Create a refund transaction in Commercetools based on a refund created from the Stripe dashboard
    """
    async_result = refund_from_stripe_task.delay(
        payment_intent_id=kwargs["payment_intent_id"],
        stripe_refund=kwargs["stripe_refund"],
    )
    return async_result.id


@log_receiver(logger)
def refund_from_paypal(**kwargs):
    """
    Create a refund transaction in Commercetools based on a refund created from the PayPal dashboard
    """
    async_result = refund_from_paypal_task.delay(
        paypal_capture_id=kwargs["paypal_capture_id"], refund=kwargs["refund"]
    )
    return async_result.id
