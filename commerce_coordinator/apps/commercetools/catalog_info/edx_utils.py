from typing import List, Union

from commercetools.platform.models import Customer as CTCustomer
from commercetools.platform.models import LineItem as CTLineItem
from commercetools.platform.models import Order as CTOrder
from commercetools.platform.models import Product as CTProduct
from commercetools.platform.models import ProductVariant as CTProductVariant

from commerce_coordinator.apps.commercetools.catalog_info.constants import (
    EDX_STRIPE_PAYMENT_INTERFACE_NAME,
    STRIPE_PAYMENT_STATUS_INTERFACE_CODE_SUCCEEDED,
    EdXFieldNames
)


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


def get_edx_payment_intent_id(order: CTOrder) -> Union[str, None]:
    for pr in order.payment_info.payments:
        pmt = pr.obj
        if pmt.payment_status.interface_code == STRIPE_PAYMENT_STATUS_INTERFACE_CODE_SUCCEEDED \
            and pmt.payment_method_info.payment_interface == EDX_STRIPE_PAYMENT_INTERFACE_NAME and \
                pmt.interface_id:
            return pmt.interface_id
    return None
