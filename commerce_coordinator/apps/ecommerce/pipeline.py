"""
Ecommerce filter pipelines
"""

from django.conf import settings
from openedx_filters import PipelineStep

from commerce_coordinator.apps.core.constants import PipelineCommand
from commerce_coordinator.apps.ecommerce.clients import EcommerceAPIClient
from commerce_coordinator.apps.ecommerce.constants import ECOMMERCE_ORDER_MANAGEMENT_SYSTEM


class GetLegacyEcommerceReceiptRedirectUrl(PipelineStep):
    """ Returns a redirect URL for an Ecommerce order if this is the active system. """

    def run_filter(self, params, active_order_management_system, order_number):
        # pylint: disable=arguments-differ, unused-argument
        if active_order_management_system != ECOMMERCE_ORDER_MANAGEMENT_SYSTEM:
            return PipelineCommand.CONTINUE.value

        return {
            "redirect_url": f'{settings.ECOMMERCE_RECEIPT_URL_BASE}{order_number}'
        }


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
        # Ecommerce starts pagination from 1, other systems from 0, since the invoker assumes 0, we're always 1 off.
        new_params['page'] = params['page'] + 1
        ecommerce_response = ecommerce_api_client.get_orders(new_params)

        order_data.append(ecommerce_response)

        return {
            "order_data": order_data
        }
