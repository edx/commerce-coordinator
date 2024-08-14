"""
Helpers for the commercetools app.
"""

import hashlib
import json
import logging
from urllib.parse import urljoin

import requests
from braze.client import BrazeClient
from commercetools import CommercetoolsError
from commercetools.platform.models import Customer, LineItem, Order, Payment, TransactionState, TransactionType
from django.conf import settings
from django.urls import reverse

from commerce_coordinator.apps.commercetools.catalog_info.edx_utils import get_edx_lms_user_name

logger = logging.getLogger(__name__)

RETIRED_USER_FIELD_DEFAULT_FMT = 'retired_user_{}'
SALT_LIST_EXCEPTION = ValueError("Salt must be a list -or- tuple of all historical salts.")


def get_braze_client():
    """ Returns a Braze client. """
    braze_api_key = settings.BRAZE_API_KEY
    braze_api_url = settings.BRAZE_API_SERVER

    if not braze_api_key or not braze_api_url:
        return None

    return BrazeClient(
        api_key=braze_api_key,
        api_url=braze_api_url,
        app_id='',
    )


def handle_commercetools_error(err: CommercetoolsError, context: str):
    error_message = f"[CommercetoolsError] {context} - Correlation ID: {err.correlation_id}, Details: {err.errors}"
    logger.error(error_message)


def send_order_confirmation_email(
    lms_user_id, lms_user_email, canvas_entry_properties
):
    """ Sends order confirmation email via Braze. """
    recipients = [{"external_user_id": lms_user_id, "attributes": {
        "email": lms_user_email,
    }}]
    canvas_id = settings.BRAZE_CT_ORDER_CONFIRMATION_CANVAS_ID

    try:
        braze_client = get_braze_client()
        if braze_client:
            braze_client.send_canvas_message(
                canvas_id=canvas_id,
                recipients=recipients,
                canvas_entry_properties=canvas_entry_properties,
            )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.exception(f"Encountered exception sending Order confirmation email. Exception: {exc}")


def format_amount_for_braze_canvas(centAmount):
    """
    Utility to convert amount to dollar with 2 decimals percision. Also adds the Dollar signs to resulting value.
    """
    return f"${(centAmount / 100):.2f}"


def extract_ct_product_information_for_braze_canvas(item: LineItem):
    """
    Utility to extract purchased product information for braze canvas properties
    """
    title = item.name.get('en-US', '')
    image_url = item.variant.images[0].url if item.variant.images else ''

    attributes_dict = {attr.name: attr.value for attr in item.variant.attributes}

    partner_name = attributes_dict.get('brand-text', '')

    price = format_amount_for_braze_canvas(item.price.value.cent_amount)

    start_date = attributes_dict.get('courserun-start', '')
    duration_low = attributes_dict.get('duration-low', '')
    duration_high = attributes_dict.get('duration-high', '')

    duration = (f"{duration_low}-{duration_high}" if duration_low and duration_high else
                duration_low or duration_high or '')

    duration_unit = attributes_dict.get('duration-unit', {}).get('label', 'weeks')

    result = {
        # TODO: Modify this to use actual product type from CT. Post R0.1
        "type": "course",
        "title": title,
        "image_url": image_url,
        "partner_name": partner_name,
        "price": price,
        "start_date": start_date,
        "duration": f"{duration} {duration_unit}" if duration else '',
    }

    return result


def extract_ct_order_information_for_braze_canvas(customer: Customer, order: Order):
    """
    Utility to extract generic order information for braze canvas properties
    """
    order_placed_on = order.last_modified_at
    formatted_order_placement_date = order_placed_on.strftime('%b %d, %Y')
    formatted_order_placement_time = order_placed_on.strftime("%I:%M %p (%Z)")
    # calculate subtotal by adding discount back if any discount is applied.
    # TODO: Post R0.1 add support for all discount types here.
    subtotal = (((order.total_price.cent_amount +
                  order.discount_on_total_price.discounted_amount.cent_amount))
                if order.discount_on_total_price else order.total_price.cent_amount)
    canvas_entry_properties = {
        "first_name": customer.first_name,
        "last_name": customer.last_name,
        "redirect_url": settings.LMS_DASHBOARD_URL,
        "view_receipt_cta_url": f"{settings.COMMERCE_COORDINATOR_URL}{reverse('frontend_app_ecommerce:order_receipt')}"
                                f"?order_number={order.order_number}",
        "purchase_date": formatted_order_placement_date,
        "purchase_time": formatted_order_placement_time,
        "subtotal":  format_amount_for_braze_canvas(subtotal),
        "total": format_amount_for_braze_canvas(order.total_price.cent_amount),
    }
    # TODO: Post R0.1 add support for all discount types here.
    if order.discount_codes and order.discount_on_total_price:
        canvas_entry_properties.update({
            "discount_code": order.discount_codes[0].discount_code.obj.code,
            "discount_value": format_amount_for_braze_canvas(
                order.discount_on_total_price.discounted_amount.cent_amount),
        })
    return canvas_entry_properties


def has_refund_transaction(payment: Payment):
    """
    Utility to determine is CT payment has an existing 'refund' transaction
    """
    for transaction in payment.transactions:
        if transaction.type == TransactionType.REFUND:  # pragma no cover
            return True
    return False


def has_full_refund_transaction(payment: Payment):
    """
    Utility to determine is CT payment has an existing 'refund' transaction for the full
    charge amount
    """
    # get charge transaction and get amount then check against refund.
    charge_amount = 0
    for transaction in payment.transactions:
        if transaction.type == TransactionType.CHARGE:
            charge_amount = transaction.amount
        if transaction.type == TransactionType.REFUND and transaction.amount == charge_amount:  # pragma no cover
            return True
    return False


def translate_stripe_refund_status_to_transaction_status(stripe_refund_status: str):
    """
    Utility to translate stripe's refund object's status attribute to a valid CT transaction state
    """
    translations = {
        'succeeded': TransactionState.SUCCESS,
        'pending': TransactionState.PENDING,
        'failed': TransactionState.FAILURE,
    }
    return translations.get(stripe_refund_status.lower(), stripe_refund_status)


def send_refund_notification(user, order_id):
    """
    Notify the support team of the refund request.

    Returns:
        bool: True if we are able to send the notification.  In this case that means we were able to create
              a ZenDesk ticket
    """

    tags = ['auto_refund']

    # Build the information for the ZenDesk ticket
    student = user
    subject = "[Refund] User-Requested Refund"
    body = generate_refund_notification_body(student, order_id)
    requester_name = get_edx_lms_user_name(student)

    return create_zendesk_ticket(requester_name, student.email, subject, body, tags)


def generate_refund_notification_body(student, order_id):
    """ Returns a refund notification message body."""

    msg = f"""A refund request has been initiated for {get_edx_lms_user_name(student)} ({student.email}).
    To process this request, please visit the link(s) below."""

    commercetools_mc_orders_url = settings.COMMERCETOOLS_MERCHANT_CENTER_ORDERS_PAGE_URL
    refund_urls = urljoin(commercetools_mc_orders_url, f'/{order_id}/')

    # emails contained in this message could contain unicode characters so encode as such
    return '{msg}\n\n{urls}'.format(msg=msg, urls='\n'.join(refund_urls))


def create_zendesk_ticket(requester_name, requester_email, subject, body, tags=None):
    """
    Create a Zendesk ticket via API.

    Returns:
        bool: False if we are unable to create the ticket for any reason
    """
    if not (settings.ZENDESK_URL and settings.ZENDESK_USER and settings.ZENDESK_API_KEY):
        logger.error('Zendesk is not configured. Cannot create a ticket.')
        return False

    # Copy the tags to avoid modifying the original list.
    tags = set(tags or [])
    tags.add('LMS')
    tags = list(tags)

    data = {
        'ticket': {
            'requester': {
                'name': requester_name,
                'email': str(requester_email)
            },
            'subject': subject,
            'comment': {'body': body},
            'tags': tags
        }
    }

    # Encode the data to create a JSON payload
    payload = json.dumps(data)

    # Set the request parameters
    url = urljoin(settings.ZENDESK_URL, '/api/v2/tickets.json')
    user = f'{settings.ZENDESK_USER}/token'
    pwd = settings.ZENDESK_API_KEY
    headers = {'content-type': 'application/json'}

    try:
        response = requests.post(url, data=payload, auth=(user, pwd), headers=headers, timeout=1)
        # Check for HTTP codes other than 201 (Created)
        if response.status_code != 201:
            logger.error('Failed to create ticket. Status: [%d], Body: [%s]', response.status_code, response.content)
            return False
        else:
            logger.debug('Successfully created ticket.')
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception(f'Failed to create ticket. Exception: {exc}')
        return False
    return True


def _create_retired_hash_withsalt(value_to_retire, salt):
    """
    Returns a retired value given a value to retire and a hash.

    Arguments:
        value_to_retire (str): Value to be retired.
        salt (str): Salt string used to modify the retired value before hashing.
    """
    return hashlib.sha256(
        salt.encode() + value_to_retire.encode('utf-8')
    ).hexdigest()


def create_retired_fields(field_value, salt_list, retired_user_field_fmt=RETIRED_USER_FIELD_DEFAULT_FMT):
    """
    Returns a retired field value based on the original lowercased field value and
    all the historical salts, from oldest to current.  The current salt is
    assumed to be the last salt in the list.

    Raises :class:`~ValueError` if the salt isn't a list of salts.

    Arguments:
        field_value (str): The value of the field to be retired.
        salt_list (list/tuple): List of all historical salts.

    Yields:
        Returns a retired value based on the original field value
        and all the historical salts, including the current salt.
    """
    if not isinstance(salt_list, (list, tuple)):
        raise SALT_LIST_EXCEPTION

    return retired_user_field_fmt.format(_create_retired_hash_withsalt(field_value.lower(), salt_list[-1]))
