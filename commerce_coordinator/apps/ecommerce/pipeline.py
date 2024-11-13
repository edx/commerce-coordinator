"""
Ecommerce filter pipelines
"""
from datetime import datetime
from logging import getLogger

from django.conf import settings
from openedx_filters import PipelineStep

from commerce_coordinator.apps.core.constants import PipelineCommand
from commerce_coordinator.apps.ecommerce.clients import EcommerceAPIClient
from commerce_coordinator.apps.ecommerce.constants import ECOMMERCE_ORDER_MANAGEMENT_SYSTEM

log = getLogger(__name__)


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

    def run_filter(self, request, params, order_data):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Arguments:
            request: request object passed through from the lms filter
            params: arguments passed through from the original order history url querystring
            order_data: any preliminary orders (from an earlier pipeline step) we want to append to
        """
        start_time = datetime.now()
        log.info("[UserOrdersView] Starting Ecommerce pipeline step execution at %s", start_time)

        new_params = params.copy()
        # Ecommerce starts pagination from 1, other systems from 0, since the invoker assumes 0, we're always 1 off.
        new_params['page'] = params['page'] + 1

        try:
            ecommerce_api_client = EcommerceAPIClient()
            ecommerce_response = ecommerce_api_client.get_orders(new_params)

            order_data.append(ecommerce_response)

            end_time = datetime.now()
            log.info(
                "[UserOrdersView] Completed Ecommerce pipeline step execution at %s with total duration: %ss",
                end_time, (end_time - start_time).total_seconds())
            return {
                "order_data": order_data
            }
        # pylint: disable=broad-exception-caught
        except Exception as ex:  # pragma no cover
            log.exception(
                "[GetEcommerceOrders] Error communicating with Ecommerce IDA. %s %s",
                ex,
                new_params
            )
            return PipelineCommand.CONTINUE.value
