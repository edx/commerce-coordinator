import decimal
from typing import List, Optional, Union

from commercetools.platform.models import Customer as CTCustomer
from commercetools.platform.models import LineItem as CTLineItem
from commercetools.platform.models import Order as CTOrder
from commercetools.platform.models import Payment as CTPayment
from commercetools.platform.models import Product as CTProduct
from commercetools.platform.models import ProductVariant as CTProductVariant
from commercetools.platform.models import TransactionType

from commerce_coordinator.apps.commercetools.catalog_info.constants import (
    PAYMENT_STATUS_INTERFACE_CODE_SUCCEEDED,
    EdXFieldNames,
    TwoUKeys
)
from commerce_coordinator.apps.commercetools.catalog_info.utils import check_is_bundle


def get_edx_product_course_run_key(prodvar_or_li: Union[CTProductVariant, CTLineItem]) -> str:
    if isinstance(prodvar_or_li, CTProductVariant):
        return prodvar_or_li.sku
    else:
        return prodvar_or_li.variant.sku


def get_edx_product_course_key(prod_or_li: Union[CTProduct, CTLineItem]) -> str:
    if isinstance(prod_or_li, CTProduct):
        return prod_or_li.key
    else:
        return prod_or_li.product_key


def get_edx_items(order: CTOrder) -> List[CTLineItem]:
    return list(filter(lambda x: True, order.line_items))


def is_edx_lms_order(order: CTOrder) -> bool:
    return len(get_edx_items(order)) >= 1


def get_edx_lms_user_id(customer: CTCustomer):
    return customer.custom.fields[EdXFieldNames.LMS_USER_ID]


def get_edx_lms_user_name(customer: CTCustomer):
    return customer.custom.fields[EdXFieldNames.LMS_USER_NAME]


def get_edx_successful_payment_info(order: CTOrder):
    for pr in order.payment_info.payments:
        pmt = pr.obj
        if pmt.payment_status.interface_code == PAYMENT_STATUS_INTERFACE_CODE_SUCCEEDED and pmt.interface_id:
            ct_payment_provider_id = pmt.payment_method_info.payment_interface
            return pmt, ct_payment_provider_id
    return None, None


def get_edx_psp_payment_id(order: CTOrder) -> Union[str, None]:
    """
    Retrieve the payment service provider (PSP) payment ID from an order.
    Currently supports:
        - Stripe: Payment Intent ID ("stripe_payment_intent_id")
        - PayPal: Order ID ("paypal_order_id")
    """
    pmt, _ = get_edx_successful_payment_info(order)
    if pmt:
        return pmt.interface_id
    return None


def get_edx_order_workflow_state_key(order: CTOrder) -> Optional[str]:
    order_workflow_state = None
    if order.state and order.state.obj:  # it should never be that we have one and not the other. # pragma no cover
        order_workflow_state = order.state.obj.key
    return order_workflow_state


def get_edx_is_sanctioned(order: CTOrder) -> bool:
    return get_edx_order_workflow_state_key(order) == TwoUKeys.SDN_SANCTIONED_ORDER_STATE


def cents_to_dollars(in_amount):
    return in_amount.cent_amount / pow(
        10, in_amount.fraction_digits
        if hasattr(in_amount, 'fraction_digits')
        else 2
    )


def get_line_item_price_to_refund(order: CTOrder, return_line_item_id: str) -> decimal.Decimal:
    """
    Calculate the refund amount for a specific line item in an order.

    Args:
        order (CTOrder): The order object containing line items.
        return_line_item_id (str): The ID of the line item to be refunded.

    Returns:
        decimal.Decimal: The refund amount for the specified line item.
    """
    if check_is_bundle(order.line_items):
        for line_item in get_edx_items(order):
            if line_item.id == return_line_item_id:
                return cents_to_dollars(line_item.total_price)

    return cents_to_dollars(order.total_price)


def get_edx_refund_info(payment: CTPayment, order: CTOrder, return_line_item_id: str) -> (decimal.Decimal, str):
    """
    Retrieve the refund amount and interaction ID for a given payment and order.

    Args:
        payment (CTPayment): The payment object containing transaction details.
        order (CTOrder): The order object containing line items.
        return_line_item_id (str): The ID of the line item to be refunded.

    Returns:
        tuple: A tuple containing the refund amount (decimal.Decimal) and the interaction ID (str).
    """
    interaction_id = None

    for transaction in payment.transactions:
        if transaction.type == TransactionType.CHARGE:  # pragma no cover
            interaction_id = transaction.interaction_id

    refund_amount = get_line_item_price_to_refund(order, return_line_item_id)

    return refund_amount, interaction_id
