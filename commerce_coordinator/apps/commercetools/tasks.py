"""
Commercetools tasks
"""

import logging

import stripe
from celery import shared_task
from commercetools import CommercetoolsError
from commercetools.platform.models import Payment
from django.conf import settings
from django.core.cache import cache

from commerce_coordinator.apps.commercetools.catalog_info.constants import (
    EDX_ANDROID_IAP_PAYMENT_INTERFACE_NAME,
    EDX_PAYPAL_PAYMENT_INTERFACE_NAME
)
from commerce_coordinator.apps.core.memcache import safe_key
from commerce_coordinator.apps.core.tasks import TASK_LOCK_EXPIRE, TASK_LOCK_RETRY, acquire_task_lock, release_task_lock

from .clients import CommercetoolsAPIClient, Refund
from .utils import has_full_refund_transaction, is_transaction_already_refunded

logger = logging.getLogger(__name__)

stripe.api_key = settings.PAYMENT_PROCESSOR_CONFIG['edx']['stripe']['secret_key']


@shared_task(bind=True, autoretry_for=(CommercetoolsError,), retry_kwargs={'max_retries': 5, 'countdown': 3})
def fulfillment_completed_update_ct_line_item_task(
    self,
    entitlement_uuid,
    order_id,
    order_version,
    line_item_id,
    item_quantity,
    from_state_id,
    to_state_key
):
    """
    Task for updating order line item on fulfillment completion via Commercetools API.
    """
    tag = "fulfillment_completed_update_ct_line_item_task"
    task_key = safe_key(key=order_id, key_prefix=tag, version='1')
    cache_key = safe_key(key=order_id, key_prefix='order_version_for'+tag, version='1')
    entitlement_info = f'and entitlement {entitlement_uuid}.' if entitlement_uuid else '.'

    def _log_error_and_release_lock(log_message):
        logger.exception(log_message)
        release_task_lock(task_key)

    def _log_info_and_release_lock(log_message):
        logger.info(log_message)
        release_task_lock(task_key)

    if not acquire_task_lock(task_key):
        logger.info(
            f"Task {task_key} is locked. "
            f"Exiting current task and retrying in {TASK_LOCK_RETRY} seconds..."
        )
        fulfillment_completed_update_ct_line_item_task.apply_async(
            kwargs={
                'entitlement_uuid': entitlement_uuid,
                'order_id': order_id,
                'order_version': order_version,
                'line_item_id': line_item_id,
                'item_quantity': item_quantity,
                'from_state_id': from_state_id,
                'to_state_key': to_state_key
            },
            countdown=TASK_LOCK_RETRY
        )
        return False

    try:
        client = CommercetoolsAPIClient()
        current_order_version = order_version

        cache_entry = cache.get(cache_key, None)

        # TODO: Remove logging after testing on stage
        if cache_entry:
            logger.info(f'[CT-{tag}] Found cache entry for order version {cache_entry} for cache key {cache_key}')
            current_order_version = cache_entry
        else:
            logger.info(f'[CT-{tag}] Cache entry not found for order version for cache key {cache_key}')

        if self.request.retries > 0:
            current_order_version = client.get_order_by_id(order_id).version

        updated_order = client.update_line_item_on_fulfillment(
            entitlement_uuid,
            order_id,
            current_order_version,
            line_item_id,
            item_quantity,
            from_state_id,
            to_state_key
        )

        cache.set(key=cache_key, value=updated_order.version, timeout=TASK_LOCK_EXPIRE)
    except CommercetoolsError as err:
        release_task_lock(task_key)
        raise err
    except Exception as exc:  # pylint: disable=broad-exception-caught
        _log_error_and_release_lock(
            f'[CT-{tag}] Unexpected error occurred while updating line item {line_item_id} for order {order_id}'
            + entitlement_info
            + 'Releasing lock.'
            + f'Exception: {exc}'
        )
        return None

    _log_info_and_release_lock(
        f'[CT-{tag}] Line item {line_item_id} updated for order {order_id}' + entitlement_info
    )

    return updated_order


@shared_task(
    autoretry_for=(CommercetoolsError,),
    retry_kwargs={"max_retries": 5, "countdown": 3},
)
def refund_from_stripe_task(
    payment_intent_id: str,
    stripe_refund: Refund,
) -> Payment | None:
    """
    Celery task for handling a refund registered in the Stripe dashboard.
    Creates a refund payment transaction record via the Commercetools API.

    Args:
        refund (dict): Refund object
        payment_intent_id (str): The Stripe payment intent identifier
    """
    client = CommercetoolsAPIClient()
    try:
        logger.info(
            f"[refund_from_stripe_task] Initiating creation of CT payment's refund transaction object "
            f"for payment Intent ID {payment_intent_id}."
        )
        payment = client.get_payment_by_key(payment_intent_id)
        if has_full_refund_transaction(payment) or is_transaction_already_refunded(
            payment, stripe_refund["id"]
        ):
            logger.info(
                f"[refund_from_stripe_task] Event 'charge.refunded' received, but Payment with ID {payment.id} "
                f"already has a full refund. Skipping task to add refund transaction"
            )
            return None
        updated_payment = client.create_return_payment_transaction(
            payment_id=payment.id,
            payment_version=payment.version,
            refund=stripe_refund,
        )
        return updated_payment
    except CommercetoolsError as err:
        logger.error(
            f"[refund_from_stripe_task] Unable to create CT payment's refund transaction "
            f"object for [ {payment.id} ] on Stripe refund {stripe_refund['id']} "
            f"with error {err.errors} and correlation id {err.correlation_id}"
        )
        return None


@shared_task(
    autoretry_for=(CommercetoolsError,),
    retry_kwargs={"max_retries": 5, "countdown": 3},
)
def refund_from_paypal_task(
    paypal_capture_id: str,
    refund: Refund,
) -> Payment | None:
    """
    Celery task for handling a refund registered in the PayPal dashboard.
    Creates a refund payment transaction record via the Commercetools API.

    Args:
        refund (dict): Refund object
        paypal_capture_id (str): The PayPal capture identifier
    """
    client = CommercetoolsAPIClient()
    try:
        payment = client.get_payment_by_transaction_interaction_id(paypal_capture_id)
        if has_full_refund_transaction(payment) or is_transaction_already_refunded(
            payment, refund["id"]
        ):
            logger.info(
                f"PayPal PAYMENT.CAPTURE.REFUNDED event received, but Payment with ID {payment.id} "
                f"already has a refund with ID: {refund.get('id')}. Skipping task to add refund transaction."
            )
            return None
        updated_payment = client.create_return_payment_transaction(
            payment_id=payment.id,
            payment_version=payment.version,
            refund=refund,
            psp=EDX_PAYPAL_PAYMENT_INTERFACE_NAME,
        )
        return updated_payment
    except CommercetoolsError as err:
        logger.error(
            f"[refund_from_paypal_task] Unable to create CT payment's refund "
            f"transaction object for payment {payment.key} "
            f"on PayPal refund {refund.get('id')} "
            f"with error {err.errors} and correlation id {err.correlation_id}"
        )
        return None


@shared_task(
    autoretry_for=(CommercetoolsError,),
    retry_kwargs={"max_retries": 5, "countdown": 3},
)
def refund_from_mobile_task(
    payment_interface: str, refund: Refund
) -> Payment | None:
    """
    Celery task for handling a refund registered in the mobile platforms (iOS/Android).
    Creates a refund payment transaction record via the Commercetools API.

    Args:
        refund (dict): Refund object
        payment_interface (str): The payment interface
    """
    client = CommercetoolsAPIClient()
    try:
        payment = client.get_payment_by_transaction_interaction_id(refund["id"])
        if has_full_refund_transaction(payment) or is_transaction_already_refunded(
            payment, refund["id"]
        ):
            logger.info(
                f"Mobile refund event received, but Payment with ID {payment.id} "
                f"already has a refund with ID: {refund.get('id')}. "
                "Skipping addition of refund transaction."
            )
        else:
            if payment_interface == EDX_ANDROID_IAP_PAYMENT_INTERFACE_NAME:
                refund["amount"] = payment.amount_planned.cent_amount
                refund["currency"] = payment.amount_planned.currency_code

            payment = client.create_return_payment_transaction(
                payment_id=payment.id,
                payment_version=payment.version,
                refund=refund,
                psp=payment_interface,
            )

        result = client.find_order_with_unprocessed_return_for_payment(
            payment_id=payment.id,
            customer_id=payment.customer.id if payment.customer else "",
        )
        if result:
            client.update_return_payment_state_after_successful_refund(
                interaction_id=refund["id"],
                payment_intent_id=refund["id"],
                payment=payment,
                order_id=result.order_id,
                order_version=result.order_version,
                return_line_item_return_ids=result.return_line_item_return_ids,
                refunded_line_item_refunds={},
                return_line_entitlement_ids={},
                should_transition_state=False,
            )

        return payment
    except CommercetoolsError as err:
        logger.error(
            f"[refund_from_mobile_task] Unable to create CT payment's refund "
            f"transaction object for payment {payment.key} "
            f"on mobile refund {refund.get('id')} "
            f"with error {err.errors} and correlation id {err.correlation_id}"
        )
        return None
