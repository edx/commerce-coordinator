"""
Commercetools Subscript Message tasks (Celery)
"""

from celery import shared_task
from celery.utils.log import get_task_logger
from commercetools import CommercetoolsError
from edx_django_utils.cache import TieredCache
from requests import RequestException
from rest_framework import status
from rest_framework.response import Response

from commerce_coordinator.apps.commercetools.catalog_info.constants import TwoUKeys
from commerce_coordinator.apps.commercetools.catalog_info.edx_utils import (
    get_edx_is_sanctioned,
    get_edx_items,
    get_edx_lms_user_id,
    get_edx_lms_user_name,
    get_edx_order_workflow_state_key,
    get_edx_payment_intent_id,
    get_edx_product_course_run_key,
    is_edx_lms_order
)
from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient
from commerce_coordinator.apps.commercetools.constants import EMAIL_NOTIFICATION_CACHE_TTL_SECS
from commerce_coordinator.apps.commercetools.serializers import OrderFulfillViewInputSerializer
from commerce_coordinator.apps.commercetools.signals import fulfill_order_placed_signal
from commerce_coordinator.apps.commercetools.utils import (
    extract_ct_order_information_for_braze_canvas,
    extract_ct_product_information_for_braze_canvas,
    send_order_confirmation_email
)
from commerce_coordinator.apps.core.memcache import safe_key

# Use the special Celery logger for our tasks
logger = get_task_logger(__name__)


# noinspection DuplicatedCode
@shared_task(autoretry_for=(RequestException, CommercetoolsError), retry_kwargs={'max_retries': 5, 'countdown': 3})
def fulfill_order_placed_message_signal_task(
    order_id,
    source_system,
):
    """Celery task for fulfilling an order placed message."""

    tag = "fulfill_order_placed_message_signal_task"

    client = CommercetoolsAPIClient()

    try:
        order = client.get_order_by_id(order_id)
    except CommercetoolsError as err:  # pragma no cover
        logger.error(f'[CT-{tag}] Order not found: {order_id} with CT error {err}, {err.errors}')
        return Response(status=status.HTTP_404_NOT_FOUND)

    try:
        customer = client.get_customer_by_id(order.customer_id)
    except CommercetoolsError as err:  # pragma no cover
        logger.error(f'[CT-{tag}]  Customer not found: {order.customer_id} for order {order_id} with '
                     f'CT error {err}, {err.errors}')
        return Response(status=status.HTTP_404_NOT_FOUND)

    if not (customer and order and is_edx_lms_order(order)):
        logger.debug(f'[CT-{tag}] order %s is not an edX order', order_id)

        return Response(status=status.HTTP_200_OK)

    logger.debug(f'[CT-{tag}] processing edX order %s', order_id)

    lms_user_id = get_edx_lms_user_id(customer)

    default_params = {
        'email_opt_in': True,  # ?? Where?
        'order_number': order.id,
        'provider_id': None,
        'edx_lms_user_id': lms_user_id,
        'course_mode': 'verified',
        'date_placed': order.last_modified_at.strftime('%b %d, %Y'),
        'source_system': source_system,
    }
    canvas_entry_properties = {"products": []}
    canvas_entry_properties.update(extract_ct_order_information_for_braze_canvas(customer, order))

    for item in get_edx_items(order):
        logger.debug(f'[CT-{tag}] processing edX order %s, line item %s', order_id, item.variant.sku)

        serializer = OrderFulfillViewInputSerializer(data={
            **default_params,
            'course_id': get_edx_product_course_run_key(item),  # likely not correct
        })

        # the following throws and thus doesn't need to be a conditional
        serializer.is_valid(raise_exception=True)  # pragma no cover

        payload = serializer.validated_data
        fulfill_order_placed_signal.send_robust(
            sender=fulfill_order_placed_message_signal_task,
            **payload
        )
        product_information = extract_ct_product_information_for_braze_canvas(item)
        canvas_entry_properties["products"].append(product_information)

    cache_key = safe_key(key=order_id, key_prefix='send_order_confirmation_email', version='1')

    cache_entry = TieredCache.get_cached_response(cache_key)

    if not cache_entry.is_found:
        send_order_confirmation_email(lms_user_id, customer.email, canvas_entry_properties)
        TieredCache.set_all_tiers(cache_key, value="SENT", django_cache_timeout=EMAIL_NOTIFICATION_CACHE_TTL_SECS)


# noinspection DuplicatedCode
@shared_task(autoretry_for=(RequestException, CommercetoolsError), retry_kwargs={'max_retries': 5, 'countdown': 3})
def fulfill_order_sanctioned_message_signal_task(
    order_id,
):
    """Celery task for an order sanctioned message."""

    tag = "fulfill_order_sanctioned_message_signal_task"

    client = CommercetoolsAPIClient()
    try:
        order = client.get_order_by_id(order_id)
    except CommercetoolsError as err:  # pragma no cover
        logger.error(f'[CT-{tag}] Order not found: {order_id} with CT error {err}, {err.errors}')
        return Response(status=status.HTTP_404_NOT_FOUND)

    order_workflow_state = get_edx_order_workflow_state_key(order)
    if not order_workflow_state:
        logger.debug(f'[CT-{tag}] order %s has no workflow/transition state', order_id)

    try:
        customer = client.get_customer_by_id(order.customer_id)
    except CommercetoolsError as err:  # pragma no cover
        logger.error(f'[CT-{tag}]  Customer not found: {order.customer_id} for order {order_id} with '
                     f'CT error {err}, {err.errors}')
        return Response(status=status.HTTP_404_NOT_FOUND)

    if not (customer and order and is_edx_lms_order(order)):
        logger.debug(f'[CT-{tag}] order %s is not an edX order', order_id)
        return Response(status=status.HTTP_200_OK)

    if get_edx_is_sanctioned(order):
        logger.debug(
            f'[CT-{tag}] order state for order %s is not %s. Actual value is %s',
            order_id,
            TwoUKeys.SDN_SANCTIONED_ORDER_STATE,
            order_workflow_state
        )

        lms_user_name = get_edx_lms_user_name(customer)
        logger.debug(f'[CT-{tag}] calling lms to deactivate user %s', lms_user_name)

        # TODO: SONIC-155 use lms_user_name to call LMS endpoint to deactivate user


# noinspection DuplicatedCode
@shared_task(autoretry_for=(RequestException, CommercetoolsError), retry_kwargs={'max_retries': 5, 'countdown': 3})
def fulfill_order_returned_signal_task(
    order_id,
):
    """Celery task for an order return (and refunded) message."""

    tag = "fulfill_order_returned_signal_task"

    client = CommercetoolsAPIClient()

    try:
        order = client.get_order_by_id(order_id)
    except CommercetoolsError as err:  # pragma no cover
        logger.error(f'[CT-{tag}] Order not found: {order_id} with CT error {err}, {err.errors}')
        return Response(status=status.HTTP_404_NOT_FOUND)

    try:
        customer = client.get_customer_by_id(order.customer_id)
    except CommercetoolsError as err:  # pragma no cover
        logger.error(f'[CT-{tag}]  Customer not found: {order.customer_id} for order {order_id} with '
                     f'CT error {err}, {err.errors}')
        return Response(status=status.HTTP_404_NOT_FOUND)

    if not (customer and order and is_edx_lms_order(order)):
        logger.debug(f'[CT-{tag}] order %s is not an edX order', order_id)
        return Response(status=status.HTTP_200_OK)

    payment_intent_id = get_edx_payment_intent_id(order)
    lms_user_name = get_edx_lms_user_name(customer)

    logger.debug(f'[CT-{tag}] calling stripe to refund payment intent %s', payment_intent_id)

    # TODO: Return payment if payment intent id is set

    for line_item in get_edx_items(order):
        course_run = get_edx_product_course_run_key(line_item)

        # TODO: Remove LMS Enrollment
        logger.debug(
            f'[CT-{tag}] calling lms to unenroll user %s in %s',
            lms_user_name, course_run
        )
