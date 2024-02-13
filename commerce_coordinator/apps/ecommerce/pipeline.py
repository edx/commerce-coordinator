"""
Ecommerce filter pipelines
"""

from django.conf import settings
from openedx_filters import PipelineStep

from commerce_coordinator.apps.core.constants import (
    UNIFIED_ORDER_HISTORY_RECEIPT_URL_KEY,
    UNIFIED_ORDER_HISTORY_SOURCE_SYSTEM_KEY,
    PipelineCommand
)
from commerce_coordinator.apps.ecommerce.clients import EcommerceAPIClient
from commerce_coordinator.apps.rollout.utils import is_legacy_order


def add_order_extended_data(ecomm_order):
    ecomm_order[UNIFIED_ORDER_HISTORY_RECEIPT_URL_KEY] = \
        f"{settings.COMMERCETOOLS_RECEIPT_URL_BASE}{ecomm_order['number']}"
    ecomm_order[UNIFIED_ORDER_HISTORY_SOURCE_SYSTEM_KEY] = "legacy_ecommerce"
    return ecomm_order


class GetLegacyEcommerceReceiptRedirectUrl(PipelineStep):

    def run_filter(self, params, order_number):  # pylint: disable=arguments-differ
        # pylint: disable=arguments-differ, unused-argument
        if is_legacy_order(order_number):
            return {
                "redirect_url": urljoin(settings.ECOMMERCE_URL, settings.ECOMMERCE_ADD_TO_BASKET_API_PATH)
            }
        return PipelineCommand.CONTINUE.value


class GetEcommerceOrders(PipelineStep):
    """
    Adds ecommerce orders to the order data list.
    """

    def run_filter(self, params, order_data):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Arguments:
            params: arguments passed through from the original order history url querystring
            order_data: any preliminary orders (from an earlier pipeline step) we want to append to
        """

        ecommerce_api_client = EcommerceAPIClient()
        new_params = params.copy()
        new_params['page'] = params['page'] + 1
        ecommerce_response = ecommerce_api_client.get_orders(new_params)

        ecommerce_response['results'] = [add_order_extended_data(x)
                                         for x in ecommerce_response['results']]
        order_data.append(ecommerce_response)

        return {
            "order_data": order_data
        }
