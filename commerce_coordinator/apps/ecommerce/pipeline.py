"""
Ecommerce filter pipelines
"""

from openedx_filters import PipelineStep

from commerce_coordinator.apps.ecommerce.clients import EcommerceApiClient


class GetEcommerceOrders(PipelineStep):
    """
    Adds ecommerce orders to the order data list.
    """

    def run_filter(self, params, order_data):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Arguments:
            params: arguments passed through from the original order history url querystring
            order_data: any preliminary orders (from earlier pipeline step) we want to append to
        """

        ecommerce_api_client = EcommerceApiClient()
        ecommerce_response = ecommerce_api_client.get_orders(params)

        order_data.append(ecommerce_response)

        return {
            "order_data": order_data
        }
