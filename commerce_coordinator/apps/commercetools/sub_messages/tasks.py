"""
Commercetools Subscription Message tasks (Celery)
"""
from datetime import datetime

from celery import shared_task
from celery.utils.log import get_task_logger
from commercetools import CommercetoolsError
from edx_django_utils.cache import TieredCache
from requests import RequestException

from commerce_coordinator.apps.commercetools.catalog_info.constants import TwoUKeys
from commerce_coordinator.apps.commercetools.catalog_info.edx_utils import (
    cents_to_dollars,
    get_edx_is_sanctioned,
    get_edx_items,
    get_edx_lms_user_id,
    get_edx_lms_user_name,
    get_edx_order_workflow_state_key,
    get_edx_product_course_run_key,
    get_edx_psp_payment_id,
    get_line_item_lms_entitlement_id,
    is_edx_lms_order
)
from commerce_coordinator.apps.commercetools.catalog_info.utils import (
    get_course_mode_from_ct_order,
    get_line_item_attribute
)
from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient
from commerce_coordinator.apps.commercetools.constants import EMAIL_NOTIFICATION_CACHE_TTL_SECS
from commerce_coordinator.apps.commercetools.filters import OrderRefundRequested
from commerce_coordinator.apps.commercetools.serializers import OrderFulfillViewInputSerializer
from commerce_coordinator.apps.commercetools.signals import (
    fulfill_order_placed_send_enroll_in_course_signal,
    fulfill_order_placed_send_entitlement_signal
)
from commerce_coordinator.apps.commercetools.utils import (
    extract_ct_order_information_for_braze_canvas,
    extract_ct_product_information_for_braze_canvas,
    send_order_confirmation_email
)
from commerce_coordinator.apps.core.constants import ISO_8601_FORMAT
from commerce_coordinator.apps.core.memcache import safe_key
from commerce_coordinator.apps.core.segment import track
from commerce_coordinator.apps.lms.clients import LMSAPIClient
from commerce_coordinator.apps.rollout.utils import (
    get_order_return_info_return_items,
    is_commercetools_line_item_already_refunded
)

# Use the special Celery logger for our tasks
logger = get_task_logger(__name__)


# noinspection DuplicatedCode
@shared_task(autoretry_for=(RequestException, CommercetoolsError), retry_kwargs={'max_retries': 5, 'countdown': 3})
def fulfill_order_placed_message_signal_task(
    order_id,
    line_item_state_id,
    source_system,
    message_id
):
    """Celery task for fulfilling an order placed message."""

    tag = "fulfill_order_placed_message_signal_task"

    logger.info(f'[CT-{tag}] Processing order {order_id}, '
                f'line item {line_item_state_id}, source system {source_system}, message id: {message_id}')

    client = CommercetoolsAPIClient()

    try:
        start_time = datetime.now()
        order = client.get_order_by_id(order_id)
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"[Performance Check] get_order_by_id call took {duration} seconds")
    except CommercetoolsError as err:  # pragma no cover
        logger.error(f'[CT-{tag}] Order not found: {order_id} with CT error {err}, {err.errors},'
                     f'message id: {message_id}')
        raise err

    try:
        customer = client.get_customer_by_id(order.customer_id)
    except CommercetoolsError as err:  # pragma no cover
        logger.error(f'[CT-{tag}]  Customer not found: {order.customer_id} for order {order_id} with '
                     f'CT error {err}, {err.errors}, message id: {message_id}')
        raise err

    if not (customer and order and is_edx_lms_order(order)):
        logger.info(f'[CT-{tag}] order {order_id} is not an edX order, message id: {message_id}')

        return True

    logger.info(f'[CT-{tag}] processing edX order {order_id}, message id: {message_id}')

    lms_user_id = get_edx_lms_user_id(customer)

    default_params = {
        'email_opt_in': True,  # ?? Where?
        'order_number': order.order_number,
        'order_id': order.id,
        'provider_id': None,
        'edx_lms_user_id': lms_user_id,
        'date_placed': order.last_modified_at.strftime(ISO_8601_FORMAT),
        'source_system': source_system,
    }
    canvas_entry_properties = {"products": []}
    canvas_entry_properties.update(extract_ct_order_information_for_braze_canvas(customer, order))

    logger.info(
        f"[CT-{tag}] Transitioning all line items for order {order.id} to {TwoUKeys.PROCESSING_FULFILMENT_STATE}"
    )
    updated_order = client.update_line_items_transition_state(
        order_id=order.id,
        order_version=order.version,
        line_items=get_edx_items(order),
        from_state_id=line_item_state_id,
        new_state_key=TwoUKeys.PROCESSING_FULFILMENT_STATE
    )

    for item in get_edx_items(order):
        logger.debug(f'[CT-{tag}] processing edX order {order_id}, line item {item.variant.sku}, '
                     f'message id: {message_id}')

        # from here we will always be transitioning from a 'Fulfillment Processing' state
        line_item_state_id = client.get_state_by_key(TwoUKeys.PROCESSING_FULFILMENT_STATE).id

        updated_order_version = updated_order.version
        default_params['order_version'] = updated_order_version

        bundle_id = (
            item.custom.fields.get(TwoUKeys.LINE_ITEM_BUNDLE_ID)
            if item.custom
            else None
        )
        canvas_entry_properties.update({'product_type': 'program' if bundle_id else 'course'})

        ct_program_product = client.get_product_by_program_id(bundle_id) if bundle_id else None

        product_title = ct_program_product.name.get('en-US', '') if ct_program_product else item.name.get('en-US', '')
        serializer = OrderFulfillViewInputSerializer(data={
            **default_params,
            # Due to CT Variant SKU storing different values for course and entitlement models
            # For bundle purchases, the course_id is the course_uuid
            # For non-bundles purchase, the course_id is the course_run_key
            'course_id': get_edx_product_course_run_key(item),
            'line_item_id': item.id,
            'course_mode': get_course_mode_from_ct_order(item),
            'item_quantity': item.quantity,
            'line_item_state_id': line_item_state_id,
            'message_id': message_id,
            'user_first_name': customer.first_name,
            'user_email': customer.email,
            'product_title': product_title,
            'product_type': item.product_type.obj.key
        })

        # the following throws and thus doesn't need to be a conditional
        serializer.is_valid(raise_exception=True)  # pragma no cover

        payload = serializer.validated_data

        if bundle_id:
            fulfill_order_placed_send_entitlement_signal.send_robust(
                sender=fulfill_order_placed_message_signal_task,
                **payload
            )
        else:
            fulfill_order_placed_send_enroll_in_course_signal.send_robust(
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

    logger.info(f'[CT-{tag}] Finished order {order_id}, '
                f'line item {line_item_state_id}, source system {source_system}, message id: {message_id}')

    return True


# noinspection DuplicatedCode
@shared_task(autoretry_for=(RequestException, CommercetoolsError), retry_kwargs={'max_retries': 5, 'countdown': 3})
def fulfill_order_sanctioned_message_signal_task(
    order_id,
    message_id
):
    """Celery task for an order sanctioned message."""

    tag = "fulfill_order_sanctioned_message_signal_task"

    logger.info(f'[CT-{tag}] Processing sanctions for {order_id}, message id: {message_id}')

    client = CommercetoolsAPIClient()
    try:
        order = client.get_order_by_id(order_id)
    except CommercetoolsError as err:  # pragma no cover
        logger.error(f'[CT-{tag}] Order not found: {order_id} with CT error {err}, {err.errors}, '
                     f'message id: {message_id}')
        return False

    order_workflow_state = get_edx_order_workflow_state_key(order)
    if not order_workflow_state:
        logger.info(f'[CT-{tag}] order {order_id} has no workflow/transition state, message id: {message_id}')

    try:
        customer = client.get_customer_by_id(order.customer_id)
    except CommercetoolsError as err:  # pragma no cover
        logger.error(f'[CT-{tag}]  Customer not found: {order.customer_id} for order {order_id} with '
                     f'CT error {err}, {err.errors}, message id: {message_id}')
        return False

    if not (customer and order and is_edx_lms_order(order)):
        logger.info(f'[CT-{tag}] order {order_id} is not an edX order, message id: {message_id}')
        return True

    if get_edx_is_sanctioned(order):
        lms_user_name = get_edx_lms_user_name(customer)
        logger.info(f'[CT-{tag}] calling lms to deactivate user {lms_user_name}, message id: {message_id}.')

        LMSAPIClient().deactivate_user(lms_user_name, message_id)

        logger.info(f'[CT-{tag}] Finished sanctions for {order_id}, message id: {message_id}')
        return True
    else:
        logger.error(
            f'[CT-{tag}] order state for order {order_id} is not {TwoUKeys.SDN_SANCTIONED_ORDER_STATE}. '
            f'Actual value is {order_workflow_state}, message id: {message_id}'
        )
        return False


# noinspection DuplicatedCode
@shared_task(autoretry_for=(RequestException, CommercetoolsError), retry_kwargs={'max_retries': 5, 'countdown': 3})
def fulfill_order_returned_signal_task(order_id, return_items, message_id):
    """Celery task for an order return (and refunded) message."""
    # pylint: disable=too-many-statements

    def _prepare_segment_event_properties(in_order, return_line_item_return_id):
        return {
            'track_plan_id': 19,
            'trigger_source': 'server-side',
            'order_id': in_order.order_number,
            'checkout_id': in_order.cart.id,
            'return_id': return_line_item_return_id,
            'total': cents_to_dollars(in_order.taxed_price.total_gross),
            'currency': in_order.taxed_price.total_gross.currency_code,
            'tax': cents_to_dollars(in_order.taxed_price.total_tax),
            'coupon': in_order.discount_codes[-1].discount_code.obj.code if in_order.discount_codes else None,
            'coupon_name': [discount.discount_code.obj.code for discount in in_order.discount_codes[:-1]],
            'discount': cents_to_dollars(
                in_order.discount_on_total_price.discounted_amount) if in_order.discount_on_total_price else 0,
            'title': get_edx_items(in_order)[0].name['en-US'] if get_edx_items(in_order) else None,
            'products': []
        }

    tag = "fulfill_order_returned_signal_task"

    logger.info(f'[CT-{tag}] Processing return for order: {order_id}, message id: {message_id}')

    client = CommercetoolsAPIClient()

    try:
        order = client.get_order_by_id(order_id)
    except CommercetoolsError as err:  # pragma no cover
        logger.error(f'[CT-{tag}] Order not found: {order_id} with CT error {err}, {err.errors}'
                     f', message id: {message_id}')
        raise err

    try:
        customer = client.get_customer_by_id(order.customer_id)
    except CommercetoolsError as err:  # pragma no cover
        logger.error(f'[CT-{tag}] Customer not found: {order.customer_id} for order {order_id} with '
                     f'CT error {err}, {err.errors}, message id: {message_id}')
        raise err

    if not (customer and order and is_edx_lms_order(order)):  # pragma no cover
        logger.info(f'[CT-{tag}] order {order_id} is not an edX order, message id: {message_id}')
        return True

    # Retrieve the payment service provider (PSP) payment ID from an order.
    # Either Stripe Payment Intent ID Or PayPal Order ID
    psp_payment_id = get_edx_psp_payment_id(order)
    lms_user_name = get_edx_lms_user_name(customer)
    lms_user_id = get_edx_lms_user_id(customer)

    logger.info(f'[CT-{tag}] calling PSP to refund payment "{psp_payment_id}", message id: {message_id}')

    return_info_return_items = get_order_return_info_return_items(order)
    # List of return line Item Ids
    return_line_item_ids = []
    # A dict containing key as line item id and value as return id
    return_line_item_return_dict = {}
    # List of return line item return ids
    return_line_item_return_ids = []
    for item in return_items:
        line_item_id = item["lineItemId"]
        return_id = item["id"]

        if not is_commercetools_line_item_already_refunded(order, line_item_id, return_info_return_items):
            return_line_item_ids.append(line_item_id)
            return_line_item_return_dict[line_item_id] = return_id
            return_line_item_return_ids.append(return_id)

    # A dict containing key as return line item id and value as lms entitlement id
    return_line_entitlement_ids = {return_line_item_return_dict.get(line_item.id):
                                   get_line_item_lms_entitlement_id(line_item) for line_item in get_edx_items(order)}

    if not return_line_item_ids:
        logger.info(f'[CT-{tag}] No return line items found for order: {order_id}, message id: {message_id}')
        return True

    # Return payment if payment id is set
    if psp_payment_id is not None:
        result = OrderRefundRequested.run_filter(
            order_id=order_id,
            return_line_item_ids=return_line_item_ids,
            return_line_item_return_ids=return_line_item_return_ids,
            return_line_entitlement_ids=return_line_entitlement_ids,
            message_id=message_id,
        )

        if 'refund_response' in result and result['refund_response']:
            if result['refund_response'] == 'charge_already_refunded':
                logger.info(f'[CT-{tag}] payment {psp_payment_id} already has refunded transaction, '
                            f'sending Slack notification, message id: {message_id}')
            else:
                logger.info(f'[CT-{tag}] payment {psp_payment_id} refunded for message id: {message_id}')

                # TODO: DISCUSS WITH SHAFQAT
                segment_event_properties = _prepare_segment_event_properties(order, return_line_item_return_ids[0])
                for line_item in get_edx_items(order):
                    if line_item.id in return_line_item_ids:
                        course_run = get_edx_product_course_run_key(line_item)
                        # TODO: Remove LMS Enrollment. To be done in SONIC-96
                        logger.info(
                            f'[CT-{tag}] calling lms to unenroll user {lms_user_name} in {course_run}'
                            f', message id: {message_id}'
                        )

                        product = {
                            'product_id': line_item.product_key,
                            'sku': line_item.variant.sku if hasattr(line_item.variant, 'sku') else None,
                            'name': line_item.name['en-US'],
                            'price': cents_to_dollars(line_item.price.value),
                            'quantity': line_item.quantity,
                            'category': get_line_item_attribute(line_item, 'primary-subject-area'),
                            'image_url': line_item.variant.images[0].url if line_item.variant.images else None,
                            'brand': get_line_item_attribute(line_item, 'brand-text'),
                            'url': get_line_item_attribute(line_item, 'url-course'),
                            'lob': get_line_item_attribute(line_item, 'lob') or 'edx',
                            'product_type': line_item.product_type.obj.name
                        }
                        segment_event_properties['products'].append(product)

                if segment_event_properties['products']:  # pragma no cover
                    # Emitting the 'Order Refunded' Segment event upon successfully processing a refund.
                    track(
                        lms_user_id=lms_user_id,
                        event='Order Refunded',
                        properties=segment_event_properties
                    )
        else:  # pragma no cover
            logger.info(f'[CT-{tag}] payment {psp_payment_id} not refunded, '
                        f'sending Slack notification, message id: {message_id}')

    logger.info(f'[CT-{tag}] Finished return for order: {order_id}, line item: {return_line_item_ids}, '
                f'message id: {message_id}')

    return True
