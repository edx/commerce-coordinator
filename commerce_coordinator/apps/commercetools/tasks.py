"""
Commercetools tasks
"""

import logging

import stripe
from celery import shared_task
from commercetools import CommercetoolsError
from django.conf import settings

from commerce_coordinator.apps.commercetools.catalog_info.constants import EDX_PAYPAL_PAYMENT_INTERFACE_NAME

from .clients import CommercetoolsAPIClient
from .utils import has_full_refund_transaction

logger = logging.getLogger(__name__)

stripe.api_key = settings.PAYMENT_PROCESSOR_CONFIG['edx']['stripe']['secret_key']


def update_line_item_on_entitlement_fulfillment_completion(
    entitlement_uuid,
    order_id,
    order_version,
    line_item_id,
    item_quantity,
    from_state_id,
    to_state_key
):
    """
    Task for updating order line item on entitlement fulfillment completion via Commercetools API.
    """
    client = CommercetoolsAPIClient()

    updated_order = client.update_line_item_on_entitlement_fulfillment(
        entitlement_uuid,
        order_id,
        order_version,
        line_item_id,
        item_quantity,
        from_state_id,
        to_state_key
    )
    return updated_order


def update_line_item_state_on_fulfillment_completion(
    order_id,
    order_version,
    line_item_id,
    item_quantity,
    from_state_id,
    to_state_key
):
    """
    Task for fulfillment completed and order line item state update via Commercetools API.
    """
    client = CommercetoolsAPIClient()

    updated_order = client.update_line_item_transition_state_on_fulfillment(
        order_id,
        order_version,
        line_item_id,
        item_quantity,
        from_state_id,
        to_state_key
    )
    return updated_order


@shared_task(autoretry_for=(CommercetoolsError,), retry_kwargs={'max_retries': 5, 'countdown': 3})
def refund_from_stripe_task(
    payment_intent_id,
    stripe_refund
):
    """
    Celery task for a refund registered in Stripe dashboard and need to create
    refund payment transaction record via Commercetools API.
    """
    client = CommercetoolsAPIClient()
    try:
        logger.info(
            f"[refund_from_stripe_task] Initiating creation of CT payment's refund transaction object "
            f"for payment Intent ID {payment_intent_id}.")
        payment = client.get_payment_by_key(payment_intent_id)
        if has_full_refund_transaction(payment):
            logger.info(f"[refund_from_stripe_task] Event 'charge.refunded' received, but Payment with ID {payment.id} "
                        f"already has a full refund. Skipping task to add refund transaction")
            return None
        updated_payment = client.create_return_payment_transaction(
            payment_id=payment.id,
            payment_version=payment.version,
            refund=stripe_refund
        )
        return updated_payment
    except CommercetoolsError as err:
        logger.error(f"[refund_from_stripe_task] Unable to create CT payment's refund transaction "
                     f"object for [ {payment.id} ] on Stripe refund {stripe_refund['id']} "
                     f"with error {err.errors} and correlation id {err.correlation_id}")
        return None


@shared_task(autoretry_for=(CommercetoolsError,), retry_kwargs={'max_retries': 5, 'countdown': 3})
def refund_from_paypal_task(
    paypal_capture_id,
    refund
):
    """
    Celery task for a refund registered in PayPal dashboard and need to create
    refund payment transaction record via Commercetools API.
    """
    client = CommercetoolsAPIClient()
    try:
        payment = client.get_payment_by_transaction_interaction_id(paypal_capture_id)
        if has_full_refund_transaction(payment):
            logger.info(f"PayPal PAYMENT.CAPTURE.REFUNDED event received, but Payment with ID {payment.id} "
                        f"already has a refund with ID: {refund.get('id')}. Skipping task to add refund transaction.")
            return None
        updated_payment = client.create_return_payment_transaction(
            payment_id=payment.id,
            payment_version=payment.version,
            refund=refund,
            psp=EDX_PAYPAL_PAYMENT_INTERFACE_NAME,
        )
        return updated_payment
    except CommercetoolsError as err:
        logger.error(f"[refund_from_paypal_task] Unable to create CT payment's refund "
                     f"transaction object for payment {payment.key} "
                     f"on PayPal refund {refund.get('id')} "
                     f"with error {err.errors} and correlation id {err.correlation_id}")
        return None
