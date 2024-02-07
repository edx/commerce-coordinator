"""
Commercetools filter pipelines
"""
import attr
from commercetools.platform.models import Customer as CTCustomer
from commercetools.platform.models import Order as CTOrder
from django.conf import settings
from openedx_filters import PipelineStep

from commerce_coordinator.apps.commercetools.catalog_info.constants import (
    EDX_STRIPE_PAYMENT_INTERFACE_NAME,
    PAYMENT_STATUS_INTERFACE_CODE_SUCCEEDED
)
from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient
from commerce_coordinator.apps.commercetools.data import order_from_commercetools
from commerce_coordinator.apps.core.constants import (
    UNIFIED_ORDER_HISTORY_RECEIPT_URL_KEY,
    UNIFIED_ORDER_HISTORY_SOURCE_SYSTEM_KEY
)


def add_order_extended_data(order: CTOrder, customer: CTCustomer):
    # The typing on asdict is too strict.
    # noinspection PyTypeChecker
    dict = attr.asdict(order_from_commercetools(order, customer))
    dict[UNIFIED_ORDER_HISTORY_RECEIPT_URL_KEY] = f"{settings.COMMERCETOOLS_RECEIPT_URL_BASE}{order.id}"
    dict[UNIFIED_ORDER_HISTORY_SOURCE_SYSTEM_KEY] = "commercetools"
    return dict


class GetCommercetoolsOrders(PipelineStep):
    """
    Adds commercetools orders to the order data list.
    """

    def run_filter(self, params, order_data):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Arguments:
            params: arguments passed through from the original order history url querystring
            order_data: any preliminary orders (from an earlier pipeline step) we want to append to
        Returns:
        """

        ct_api_client = CommercetoolsAPIClient()
        ct_orders = ct_api_client.get_orders_for_customer(
            edx_lms_user_id=params["edx_lms_user_id"],
            limit=params["page_size"],
            offset=params["page"] * params["page_size"]
        )

        converted_orders = [add_order_extended_data(x, ct_orders[1])
                            for x in ct_orders[0].results]

        order_data.append(
            ct_orders[0].rebuild(converted_orders)
        )

        return {
            "order_data": order_data
        }


class FetchOrderDetails(PipelineStep):
    """ Fetch the order Details and if we can, set the PaymentIntent """

    def run_filter(self, params, order_number):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Arguments:
            params: arguments passed through from the original order history url querystring
            order_number: Order number (for now this is an order.id, but this should change in the future)
        Returns:
        """

        ct_api_client = CommercetoolsAPIClient()
        ct_order = ct_api_client.get_order_by_id(order_id=order_number)

        ret_val = {
            "order_data": ct_order
        }

        for pr in ct_order.payment_info.payments:
            pmt = pr.obj
            if pmt.payment_status.interface_code == PAYMENT_STATUS_INTERFACE_CODE_SUCCEEDED \
                and pmt.payment_method_info.payment_interface == EDX_STRIPE_PAYMENT_INTERFACE_NAME and \
                    pmt.interface_id:
                ret_val['payment_intent_id'] = pmt.interface_id

        return ret_val
