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
    try:
        updated_order = client.update_line_item_transition_state_on_fulfillment(
            order_id,
            order_version,
            line_item_id,
            item_quantity,
            from_state_id,
            to_state_key
        )
        return updated_order
    except CommercetoolsError as err:
        logger.error(f"Unable to update line item [ {line_item_id} ] state on fulfillment "
                     f"result with error {err.errors} and correlation id {err.correlation_id}")
        return None


@shared_task(autoretry_for=(CommercetoolsError,), retry_kwargs={'max_retries': 5, 'countdown': 3})
def refund_from_stripe_task(
    payment_intent_id,
    stripe_refund
):
    """
    Celery task for a refund registered in Stripe dashboard and need to create
    refund payment transaction record via Commercetools API.
    """
    # Celery serializes stripe_refund to a dict, so we need to explictly convert it back to a Refund object
    client = CommercetoolsAPIClient()
    try:
        payment = client.get_payment_by_key(payment_intent_id)
        if has_full_refund_transaction(payment):
            logger.info(f"Stripe charge.refunded event received, but Payment with ID {payment.id} "
                        f"already has a full refund. Skipping task to add refund transaction")
            return None
        updated_payment = client.create_return_payment_transaction(
            payment_id=payment.id,
            payment_version=payment.version,
            refund=stripe_refund
        )
        return updated_payment
    except CommercetoolsError as err:
        logger.error(f"Unable to create refund transaction for payment [ {payment.id} ] "
                     f"on Stripe refund {stripe_refund.id} "
                     f"with error {err.errors} and correlation id {err.correlation_id}")
        return None


@shared_task(autoretry_for=(CommercetoolsError,), retry_kwargs={'max_retries': 5, 'countdown': 3})
def refund_from_paypal_task(
    paypal_order_id,
    refund
):
    """
    Celery task for a refund registered in PayPal dashboard and need to create
    refund payment transaction record via Commercetools API.
    """
    client = CommercetoolsAPIClient()
    try:
        payment = client.get_payment_by_key(paypal_order_id)
        updated_payment = client.create_return_payment_transaction(
            payment_id=payment.id,
            payment_version=payment.version,
            refund=refund,
            psp=EDX_PAYPAL_PAYMENT_INTERFACE_NAME,
        )
        return updated_payment
    except CommercetoolsError as err:
        logger.error(f"Unable to create refund transaction for payment [ {paypal_order_id} ] "
                     f"on PayPal refund {refund.id} "
                     f"with error {err.errors} and correlation id {err.correlation_id}")
        return None
