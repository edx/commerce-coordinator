"""
Commercetools signals and receivers.
"""

import logging

from commerce_coordinator.apps.commercetools.catalog_info.constants import TwoUKeys
from commerce_coordinator.apps.commercetools.tasks import (
    fulfillment_completed_update_ct_line_item_task,
    refund_from_mobile_task,
    refund_from_paypal_task,
    refund_from_stripe_task,
    revoke_line_mobile_order_task
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
        order_number=kwargs["order_number"],
    )
    return async_result.id


@log_receiver(logger)
def refund_from_paypal(**kwargs):
    """
    Create a refund transaction in Commercetools based on a refund created from the PayPal dashboard
    """
    async_result = refund_from_paypal_task.delay(
        paypal_capture_id=kwargs["paypal_capture_id"],
        refund=kwargs["refund"],
        order_number=kwargs["order_number"]
    )
    return async_result.id


@log_receiver(logger)
def refund_from_mobile(**kwargs):
    """
    Create a refund transaction in Commercetools based on a refund created from mobile platforms (iOS/Android).
    """
    async_result = refund_from_mobile_task.delay(
        payment_interface=kwargs["payment_interface"],
        refund=kwargs["refund"],
        redirect_to_legacy_enabled=kwargs.get("redirect_to_legacy_enabled", False),
        legacy_redirect_payload=kwargs.get("legacy_redirect_payload", b''),
    )
    return async_result.id


@log_receiver(logger)
def revoke_line_mobile_order(**kwargs):
    """
    Trigger the refund_from_mobile_task to handle a refund transaction
    for mobile platforms (iOS/Android) in Commercetools.
    """
    async_result = revoke_line_mobile_order_task.delay(payment_id=kwargs["payment_id"])
    return async_result.id
