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
    EDX_STRIPE_PAYMENT_INTERFACE_NAME,
    EDX_PAYPAL_PAYMENT_INTERFACE_NAME,
    PAYMENT_STATUS_INTERFACE_CODE_SUCCEEDED,
    EdXFieldNames,
    TwoUKeys
)
from commerce_coordinator.apps.commercetools.catalog_info.utils import typed_money_to_string


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


def get_edx_successful_stripe_payment(order: CTOrder) -> Union[CTPayment, None]:
    for pr in order.payment_info.payments:
        pmt = pr.obj
        if pmt.payment_status.interface_code == PAYMENT_STATUS_INTERFACE_CODE_SUCCEEDED \
            and pmt.payment_method_info.payment_interface == EDX_STRIPE_PAYMENT_INTERFACE_NAME and \
                pmt.interface_id:
            return pmt
    return None


# TODO remove get_edx_successful_stripe_payment if there is no more use.
def get_edx_successful_payment_info(order: CTOrder):
    for pr in order.payment_info.payments:
        pmt = pr.obj
        if pmt.payment_status.interface_code == PAYMENT_STATUS_INTERFACE_CODE_SUCCEEDED and pmt.interface_id:
            return pmt, pmt.payment_method_info.payment_interface
    return None, None


def get_edx_payment_intent_id(order: CTOrder) -> Union[str, None]:
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


def get_edx_refund_amount(order: CTOrder) -> decimal:
    refund_amount = decimal.Decimal(0.00)
    pmt, _ = get_edx_successful_payment_info(order)
    for transaction in pmt.transactions:
        if transaction.type == TransactionType.CHARGE:  # pragma no cover
            refund_amount += decimal.Decimal(typed_money_to_string(transaction.amount, money_as_decimal_string=True))
    return refund_amount
