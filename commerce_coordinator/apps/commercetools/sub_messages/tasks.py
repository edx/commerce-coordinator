"""
Commercetools Subscription Message tasks (Celery)
"""
from celery import shared_task
from celery.utils.log import get_task_logger
from commercetools import CommercetoolsError
from edx_django_utils.cache import TieredCache
from requests import RequestException

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
from commerce_coordinator.apps.core.segment import track

# Use the special Celery logger for our tasks
logger = get_task_logger(__name__)


# noinspection DuplicatedCode
@shared_task(autoretry_for=(RequestException, CommercetoolsError), retry_kwargs={'max_retries': 5, 'countdown': 3})
def fulfill_order_placed_message_signal_task(
    order_id,
    line_item_state_id,
    source_system,
):
    """Celery task for fulfilling an order placed message."""

    tag = "fulfill_order_placed_message_signal_task"

    client = CommercetoolsAPIClient()

    try:
        order = client.get_order_by_id(order_id)
    except CommercetoolsError as err:  # pragma no cover
        logger.error(f'[CT-{tag}] Order not found: {order_id} with CT error {err}, {err.errors}')
        return False

    try:
        customer = client.get_customer_by_id(order.customer_id)
    except CommercetoolsError as err:  # pragma no cover
        logger.error(f'[CT-{tag}]  Customer not found: {order.customer_id} for order {order_id} with '
                     f'CT error {err}, {err.errors}')
        return False

    if not (customer and order and is_edx_lms_order(order)):
        logger.debug(f'[CT-{tag}] order %s is not an edX order', order_id)

        return True

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
        updated_order = client.update_line_item_transition_state_on_fulfillment(
            order.id,
            order.version,
            item.id,
            item.quantity,
            line_item_state_id,
            TwoUKeys.PROCESSING_FULFILMENT_STATE
        )

        # from here we will always be transitioning from a 'Fulfillment Processing' state
        line_item_state_id = client.get_state_by_key(TwoUKeys.PROCESSING_FULFILMENT_STATE).id

        updated_order_version = updated_order.version
        default_params['order_version'] = updated_order_version

        serializer = OrderFulfillViewInputSerializer(data={
            **default_params,
            'course_id': get_edx_product_course_run_key(item),  # likely not correct
            'line_item_id': item.id,
            'item_quantity': item.quantity,
            'line_item_state_id': line_item_state_id
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

    if not cache_entry.is_found:  # pragma no cover
        send_order_confirmation_email(lms_user_id, customer.email, canvas_entry_properties)
        TieredCache.set_all_tiers(cache_key, value="SENT", django_cache_timeout=EMAIL_NOTIFICATION_CACHE_TTL_SECS)

    return True


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
        return False

    order_workflow_state = get_edx_order_workflow_state_key(order)
    if not order_workflow_state:
        logger.debug(f'[CT-{tag}] order %s has no workflow/transition state', order_id)

    try:
        customer = client.get_customer_by_id(order.customer_id)
    except CommercetoolsError as err:  # pragma no cover
        logger.error(f'[CT-{tag}]  Customer not found: {order.customer_id} for order {order_id} with '
                     f'CT error {err}, {err.errors}')
        return False

    if not (customer and order and is_edx_lms_order(order)):
        logger.debug(f'[CT-{tag}] order %s is not an edX order', order_id)
        return True

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

    return True


# noinspection DuplicatedCode
@shared_task(autoretry_for=(RequestException, CommercetoolsError), retry_kwargs={'max_retries': 5, 'countdown': 3})
def fulfill_order_returned_signal_task(
    order_id,
):
    """Celery task for an order return (and refunded) message."""

    def _get_line_item_attribute(in_line_item, in_attribute_name):  # pragma no cover
        """Utility to get line item's attribute's value."""
        attribute_value = None
        for attribute in in_line_item.variant.attributes:
            if attribute.name == in_attribute_name and hasattr(attribute, 'value'):
                if isinstance(attribute.value, dict):
                    attribute_value = attribute.value.get('label', None)
                elif isinstance(attribute.value, str):
                    attribute_value = attribute.value
                break

        return attribute_value

    def _cents_to_dollars(in_amount):
        return in_amount.cent_amount / pow(
            10, in_amount.fraction_digits
            if hasattr(in_amount, 'fraction_digits')
            else 2
        )

    def _prepare_segment_event_properties(in_order):  # pragma no cover
        return {
            'track_plan_id': 19,
            'trigger_source': 'server-side',
            'order_id': in_order.id,
            'checkout_id': in_order.cart.id,
            'return_id': '',  # TODO: [https://2u-internal.atlassian.net/browse/SONIC-391] Set CT return ID here.
            'total': _cents_to_dollars(in_order.taxed_price.total_gross),
            'currency': in_order.taxed_price.total_gross.currency_code,
            'tax': _cents_to_dollars(in_order.taxed_price.total_tax),
            'coupon': in_order.discount_codes[-1].discount_code.obj.code if in_order.discount_codes else None,
            'coupon_name': [discount.discount_code.obj.code for discount in in_order.discount_codes[:-1]],
            'discount': _cents_to_dollars(
                in_order.discount_on_total_price.discounted_amount) if in_order.discount_on_total_price else 0,
            'title': get_edx_items(in_order)[0].name['en-US'] if get_edx_items(in_order) else None,
            'products': []
        }

    tag = "fulfill_order_returned_signal_task"

    client = CommercetoolsAPIClient()

    try:
        order = client.get_order_by_id(order_id)
    except CommercetoolsError as err:  # pragma no cover
        logger.error(f'[CT-{tag}] Order not found: {order_id} with CT error {err}, {err.errors}')
        return False

    try:
        customer = client.get_customer_by_id(order.customer_id)
    except CommercetoolsError as err:  # pragma no cover
        logger.error(f'[CT-{tag}]  Customer not found: {order.customer_id} for order {order_id} with '
                     f'CT error {err}, {err.errors}')
        return False

    if not (customer and order and is_edx_lms_order(order)):
        logger.debug(f'[CT-{tag}] order %s is not an edX order', order_id)
        return True

    payment_intent_id = get_edx_payment_intent_id(order)
    lms_user_name = get_edx_lms_user_name(customer)
    lms_user_id = get_edx_lms_user_id(customer)

    logger.debug(f'[CT-{tag}] calling stripe to refund payment intent %s', payment_intent_id)

    # TODO: Return payment if payment intent id is set

    segment_event_properties = _prepare_segment_event_properties(order)  # pragma no cover

    for line_item in get_edx_items(order):
        course_run = get_edx_product_course_run_key(line_item)

        # TODO: Remove LMS Enrollment

        logger.debug(
            f'[CT-{tag}] calling lms to unenroll user %s in %s',
            lms_user_name, course_run
        )

        product = {
            'product_id': line_item.product_key,
            'sku': line_item.variant.sku if hasattr(line_item.variant, 'sku') else None,
            'name': line_item.name['en-US'],
            'price': _cents_to_dollars(line_item.price.value),
            'quantity': line_item.quantity,
            'category': _get_line_item_attribute(line_item, 'primarySubjectArea'),
            'image_url': line_item.variant.images[0].url if line_item.variant.images else None,
            'brand': _get_line_item_attribute(line_item, 'brand-text')
        }
        segment_event_properties['products'].append(product)

    if segment_event_properties['products']:  # pragma no cover
        # Emitting the 'Order Refunded' Segment event upon successfully processing a refund.
        track(
            lms_user_id=lms_user_id,
            event='Order Refunded',
            properties=segment_event_properties
        )

    return True