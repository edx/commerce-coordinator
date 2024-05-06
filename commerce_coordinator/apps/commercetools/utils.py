"""
Helpers for the commercetools app.
"""

import logging

from braze.client import BrazeClient
from commercetools.platform.models import Customer, LineItem, Order, Payment, TransactionState, TransactionType
from django.conf import settings
from django.urls import reverse

logger = logging.getLogger(__name__)


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

    start_date = attributes_dict.get('courserun_start', '')
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
                                f"?order_number={order.id}",
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
