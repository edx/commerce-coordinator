"""
Commercetools tasks
"""
import stripe
from celery import shared_task
from celery.utils.log import get_task_logger
from commercetools import CommercetoolsError
from commercetools.platform.models import Payment
from django.conf import settings
from iso4217 import Currency

from commerce_coordinator.apps.commercetools.catalog_info.constants import (
    EDX_ANDROID_IAP_PAYMENT_INTERFACE_NAME,
    EDX_IOS_IAP_PAYMENT_INTERFACE_NAME,
    EDX_PAYPAL_PAYMENT_INTERFACE_NAME
)
from commerce_coordinator.apps.commercetools.catalog_info.edx_utils import (
    check_is_bundle,
    get_edx_items,
    get_edx_line_item,
    get_edx_line_item_state,
    get_edx_lms_user_id,
    get_edx_lms_user_name,
    get_edx_product_course_run_key
)
from commerce_coordinator.apps.commercetools.catalog_info.utils import get_line_item_attribute, get_product_data
from commerce_coordinator.apps.core.memcache import safe_key
from commerce_coordinator.apps.core.segment import track
from commerce_coordinator.apps.core.tasks import TASK_LOCK_RETRY, acquire_task_lock, release_task_lock
from commerce_coordinator.apps.ecommerce.clients import EcommerceAPIClient
from commerce_coordinator.apps.iap.signals import revoke_line_mobile_order_signal
from commerce_coordinator.apps.order_fulfillment.clients import OrderFulfillmentAPIClient
from commerce_coordinator.apps.order_fulfillment.serializers import OrderRevokeLineRequestSerializer

from .clients import CommercetoolsAPIClient, Refund
from .utils import (
    convert_ct_cent_amount_to_localized_price,
    get_lob_from_variant_attr,
    has_full_refund_transaction,
    is_transaction_already_refunded,
    prepare_segment_event_properties
)

logger = get_task_logger(__name__)

stripe.api_key = settings.PAYMENT_PROCESSOR_CONFIG['edx']['stripe']['secret_key']


@shared_task(bind=True, autoretry_for=(CommercetoolsError,), retry_kwargs={'max_retries': 5, 'countdown': 3})
def fulfillment_completed_update_ct_line_item_task(
    self,  # pylint: disable=unused-argument
    entitlement_uuid,
    order_id,
    line_item_id,
    to_state_key
):
    """
    Task for updating order line item on fulfillment completion via Commercetools API.
    """
    tag = "fulfillment_completed_update_ct_line_item_task"
    task_key = safe_key(key=order_id, key_prefix=tag, version='1')
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
                'line_item_id': line_item_id,
                'to_state_key': to_state_key
            },
            countdown=TASK_LOCK_RETRY
        )
        return False

    try:
        client = CommercetoolsAPIClient()
        order = client.get_order_by_id(order_id)
        current_order_version = order.version

        line_item = get_edx_line_item(order.line_items, line_item_id)

        updated_order = client.update_line_item_on_fulfillment(
            entitlement_uuid,
            order_id,
            current_order_version,
            line_item_id,
            line_item.quantity,
            get_edx_line_item_state(line_item),
            to_state_key
        )
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
    order_number: str | None = None
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
        total_in_dollars = convert_ct_cent_amount_to_localized_price(
            stripe_refund["amount"],
            Currency(stripe_refund["currency"].upper()).exponent,
        )
        _send_segement_event(
            order_number=order_number,
            total_in_dollars=str(total_in_dollars),
            client=client,
        )
        return updated_payment
    except CommercetoolsError as err:
        logger.error(
            f"[refund_from_stripe_task] Unable to create CT payment's refund transaction "
            f"object for [ {payment.id} ] on Stripe refund {stripe_refund['id']} "
            f"with error {err.errors} and correlation id {err.correlation_id}"
        )
        raise err


def _send_segement_event(*, order_number, total_in_dollars, client) -> None:
    """
    Send Segment event for order refund.
    Args:
        order_number (str): The order number for which the refund is processed.
    """
    tag = "order_refund_segment_event"

    try:
        order = client.get_order_by_number(order_number)

    except CommercetoolsError as err:  # pragma no cover
        logger.error(f'[CT-{tag}] Order not found: {order_number} with CT error {err}, {err.errors}'
                     f', ')
        raise err

    try:
        customer = client.get_customer_by_id(order.customer_id)
    except CommercetoolsError as err:  # pragma no cover
        logger.error(f'[CT-{tag}] Customer not found: {order.customer_id} with error {err}, {err.errors}')
        raise err

    lms_user_id = get_edx_lms_user_id(customer)
    line_item = order.line_items[0]
    is_bundle = check_is_bundle(order.line_items)
    product = get_product_data(line_item, is_bundle)
    event_title = line_item.name['en-US']
    segment_event_properties = prepare_segment_event_properties(
        order=order,
        total_in_dollars=total_in_dollars,
        line_item_ids=[line_item.id],
    )

    segment_event_properties['products'].append(product)
    if segment_event_properties['products']:  # pragma no cover
        segment_event_properties['title'] = event_title
        # Emitting the 'Order Refunded' Segment event upon successfully processing a refunds.
        track(
            lms_user_id=lms_user_id,
            event='Order Refunded',
            properties=segment_event_properties
        )
        logger.info(f'[CT-{tag}] Customer found: {order.customer_id} for order {order.id} and '
                    f'send refund segment event')


@shared_task(
    autoretry_for=(CommercetoolsError,),
    retry_kwargs={"max_retries": 5, "countdown": 3},
)
def refund_from_paypal_task(
    paypal_capture_id: str,
    refund: Refund,
    order_number: str,
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
        if not payment:
            logger.warning(
                "[refund_from_paypal_task] PayPal PAYMENT.CAPTURE.REFUNDED event "
                "received, but could not find a CT Payment for PayPal captureID: "
                f"{paypal_capture_id}."
            )
            return None
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
        _send_segement_event(
            order_number=order_number,
            total_in_dollars=refund["amount"],
            client=client,
        )
        return updated_payment
    except CommercetoolsError as err:
        logger.error(
            f"[refund_from_paypal_task] Unable to create CT payment's refund "
            f"transaction object for payment {payment.key} "
            f"on PayPal refund {refund.get('id')} "
            f"with error {err.errors} and correlation id {err.correlation_id}"
        )
        raise err


@shared_task(
    autoretry_for=(CommercetoolsError,),
    retry_kwargs={"max_retries": 5, "countdown": 3},
)
def refund_from_mobile_task(
    payment_interface: str,
    refund: Refund,
    redirect_to_legacy_enabled: bool,
    legacy_redirect_payload: bytes,
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
        if not payment:
            logger.warning(
                "[refund_from_mobile_task] Mobile refund event received, but "
                f"could not find a CT Payment for transaction ID: {refund['id']} "
                f"of payment processor: {payment_interface}."
            )
            if redirect_to_legacy_enabled:
                if payment_interface == EDX_IOS_IAP_PAYMENT_INTERFACE_NAME:
                    logger.info(
                        "[refund_from_mobile_task] Calling legacy ecommerce ios refund "
                        f"for transaction ID: {refund['id']}."
                    )
                    EcommerceAPIClient().refund_for_ios(payload=legacy_redirect_payload)
            return None
        if has_full_refund_transaction(payment) or is_transaction_already_refunded(
            payment, refund["id"]
        ):
            logger.info(
                "[refund_from_mobile_task] Mobile refund event received, but Payment "
                f"with ID {payment.id} already has a refund with ID: {refund['id']}. "
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

            revoke_line_mobile_order_signal.send_robust(
                sender=refund_from_mobile_task, payment_id=payment.id
            )

            logger.info(
                "[refund_from_mobile_task] Created refund transaction and triggered "
                f"revoke line for Payment with ID {payment.id} and transaction ID: "
                f"{refund['id']} of payment processor: {payment_interface}."
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
            f"[refund_from_mobile_task] Unable to refund for mobile for "
            f"transaction ID: {refund['id']} of payment processor: {payment_interface}."
            f"with error {err.errors} and correlation id {err.correlation_id}"
        )
        raise err


@shared_task(
    autoretry_for=(CommercetoolsError,),
    retry_kwargs={"max_retries": 5, "countdown": 3},
)
def revoke_line_mobile_order_task(payment_id: str):
    """
    Celery task to unenroll a user from a course based on the given payment ID in mobile order.

    Steps:
    - Retrieve the order using the payment ID.
    - Get the course run key from the order line item.
    - Resolve LMS user from Commercetools customer.
    - Call the Order Fulfillment API to revoke the enrollment.

    Args:
        payment_id (str): The ID of the payment linked to the order.
    """

    tag = "revoke_line_mobile_order_task"

    logger.info(f"[CT-{tag}] Starting unenrollment task for payment_id {payment_id}")

    client = CommercetoolsAPIClient()

    order = client.get_order_by_payment_id(payment_id)
    customer = client.get_customer_by_id(order.customer_id)

    item_to_unenroll = get_edx_items(order)[0]
    course_run_key = get_edx_product_course_run_key(item_to_unenroll)
    course_mode = get_line_item_attribute(item_to_unenroll, "mode")

    lms_user_id = get_edx_lms_user_id(customer)
    lms_user_username = get_edx_lms_user_name(customer)

    logging_data = {
        "order_id": order.id,
        "payment_id": payment_id,
        "customer_id": customer.id,
        "course_run_key": course_run_key,
        "lms_user_id": lms_user_id,
        "lms_user_name": lms_user_username,
        "course_mode": course_mode,
    }

    lob = get_lob_from_variant_attr(item_to_unenroll.variant) or "edx"
    serializer = OrderRevokeLineRequestSerializer(data={
        "edx_lms_username": lms_user_username,
        "course_run_key": course_run_key,
        "course_mode": course_mode,
        "lob": lob,
    })
    serializer.is_valid(raise_exception=True)

    OrderFulfillmentAPIClient().revoke_line(
        payload=serializer.validated_data,
        logging_data=logging_data,
    )

    logger.info(f"[CT-{tag}] Successfully called revoke_line for user {lms_user_username} "
                f"on course {course_run_key} and {logging_data}")

    return True
