"""
Commercetools tasks
"""

import stripe
from django.conf import settings
from celery import shared_task
import logging

from commercetools import CommercetoolsError

from .clients import CommercetoolsAPIClient

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
    #import pdb; pdb.set_trace()
    # Celery serializes stripe_refund to a dict, so we need to explictly convert it back to a Refund object
    stripe_refund = stripe.Refund.construct_from(stripe_refund, stripe.api_key)
    client = CommercetoolsAPIClient()
    try:
        payment = client.get_payment_by_key(payment_intent_id)
        updated_payment = client.create_return_payment_transaction(
            payment_id=payment.id,
            payment_version=payment.version,
            stripe_refund=stripe_refund
        )
        return updated_payment
    except CommercetoolsError as err:
        logger.error(f"Unable to create refund transaction for payment [ {payment.id} ] on Stripe refund {stripe_refund.id} "
                     f"with error {err.errors} and correlation id {err.correlation_id}")
        return None
