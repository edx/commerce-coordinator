"""
Helpers for the commercetools app.
"""

import hashlib
import logging

from braze.client import BrazeClient
from commercetools import CommercetoolsError
from commercetools.platform.models import (
    CentPrecisionMoney,
    Customer,
    LineItem,
    Order,
    Payment,
    TransactionState,
    TransactionType,
    TypedMoney
)
from django.conf import settings
from django.urls import reverse

from commerce_coordinator.apps.commercetools.catalog_info.edx_utils import cents_to_dollars

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


def handle_commercetools_error(context_prefix, err: CommercetoolsError, context: str, is_info=False):
    """Handles commercetools errors."""
    error_message = (f"[CommercetoolsError] {context_prefix} {context} "
                     f"- Correlation ID: {err.correlation_id}, Details: {err.errors}")
    if is_info:
        logger.info(error_message)
    else:
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


def send_fulfillment_error_email(
    lms_user_id, lms_user_email, canvas_entry_properties
):
    """ Sends fulfillment error email via Braze. """
    recipients = [{"external_user_id": lms_user_id, "attributes": {
        "email": lms_user_email,
    }}]
    canvas_id = settings.BRAZE_CT_FULFILLMENT_UNSUPPORTED_MODE_ERROR_CANVAS_ID

    try:
        braze_client = get_braze_client()
        if braze_client:
            braze_client.send_canvas_message(
                canvas_id=canvas_id,
                recipients=recipients,
                canvas_entry_properties=canvas_entry_properties,
            )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.exception(f"Encountered exception sending Fulfillment error email. Exception: {exc}")


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
        "title": title,
        "image_url": image_url,
        "partner_name": partner_name,
        "price": price,
        "start_date": start_date,
        "duration": f"{duration} {duration_unit}" if duration else '',
    }

    return result


def calculate_total_discount_on_order(order: Order, line_item_ids=None) -> TypedMoney:
    """Calculate discount for cart level and line item level."""
    # discount amount on cart from a cart discount with target total price
    discount_on_total_price = 0
    if hasattr(order, 'discount_on_total_price') and order.discount_on_total_price:
        discount_on_total_price = order.discount_on_total_price.discounted_amount.cent_amount

    filtered_line_items = order.line_items
    if line_item_ids:
        filtered_line_items = [line_item for line_item in order.line_items if line_item.id in line_item_ids]

    cart_discount_on_line_items = sum(
        discount.discounted_amount.cent_amount
        for item in filtered_line_items
        for discounted_price in item.discounted_price_per_quantity
        for discount in discounted_price.discounted_price.included_discounts
    )

    # discount amount on item from a product discount on a line item
    product_discount_on_line_items = sum(
        (item.price.value.cent_amount - item.price.discounted.value.cent_amount)
        for item in filtered_line_items
        if getattr(item.price, "discounted", False)
    )

    total_discount_cent_amount = discount_on_total_price + cart_discount_on_line_items + product_discount_on_line_items

    total_discount = CentPrecisionMoney(
        cent_amount=total_discount_cent_amount,
        currency_code=order.total_price.currency_code,
        fraction_digits=order.total_price.fraction_digits
    )
    return total_discount


def extract_ct_order_information_for_braze_canvas(customer: Customer, order: Order):
    """
    Utility to extract generic order information for braze canvas properties
    """
    order_placed_on = order.last_modified_at
    formatted_order_placement_date = order_placed_on.strftime('%b %d, %Y')
    formatted_order_placement_time = order_placed_on.strftime("%I:%M %p (%Z)")
    total_discount = calculate_total_discount_on_order(order)
    # calculate subtotal by adding discount back if any discount is applied.
    subtotal = order.total_price.cent_amount + total_discount.cent_amount
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

    if total_discount and total_discount.cent_amount != 0:
        canvas_entry_properties.update({
            "discount_code": order.discount_codes[0].discount_code.obj.code if order.discount_codes else None,
            "discount_value": format_amount_for_braze_canvas(total_discount.cent_amount),
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
    refunded_amount = 0
    for transaction in payment.transactions:
        if transaction.type == TransactionType.CHARGE:
            charge_amount += cents_to_dollars(transaction.amount)
        if transaction.type == TransactionType.REFUND:  # pragma no cover
            refunded_amount += cents_to_dollars(transaction.amount)

    return refunded_amount == charge_amount


def is_transaction_already_refunded(payment: Payment, psp_refund_transaction_id: str):
    """
    Utility to determine if a transaction has already been refunded
    """
    for transaction in payment.transactions:
        if transaction.type == TransactionType.REFUND and transaction.interaction_id == psp_refund_transaction_id:
            return True

    return False


def find_refund_transaction(payment: Payment, psp_refund_transaction_id: str):
    """
    Utility to find the refund transaction in a payment
    """
    for transaction in payment.transactions:
        if transaction.type == TransactionType.REFUND and transaction.interaction_id == psp_refund_transaction_id:
            return transaction.id
    return ''


def find_latest_refund(payment: Payment):
    """
    Utility to find the latest refund transaction in a payment, given payment transacations are sorted.
    """
    sorted_transactions = sorted(
        payment.transactions, key=lambda transaction: transaction.timestamp, reverse=True
    )
    for transaction in sorted_transactions:
        if transaction.type == TransactionType.REFUND:
            return transaction.id
    return ''


def translate_refund_status_to_transaction_status(refund_status: str):
    """
    Utility to translate refund object's status attribute to a valid CT transaction state
    """
    translations = {
        'succeeded': TransactionState.SUCCESS,
        'completed': TransactionState.SUCCESS,
        'pending': TransactionState.PENDING,
        'failed': TransactionState.FAILURE,
        'canceled': TransactionState.FAILURE,
    }
    return translations.get(refund_status.lower(), TransactionState.SUCCESS)


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

def get_lob_from_variant_attr(variant):
    """
    Returns line of business from item's variant attributes

    Arguments:
    variant (dict): order line item variant

    """
    for attr in variant.attributes:
        if attr.name == 'lob':
            return attr.value
    return None
