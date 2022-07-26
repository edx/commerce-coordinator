"""
order app filter pipeline implementations
"""

from openedx_filters import PipelineStep

from commerce_coordinator.apps.ecommerce.clients import EcommerceApiClient


class GetEcommerceOrders(PipelineStep):
    """
    Adds ecommerce orders to the order data list.
    """
    def run_filter(self, order_data, *args, **kwargs):  # pylint: disable=arguments-differ

        ecommerce_api_client = EcommerceApiClient()
        ecommerce_response = ecommerce_api_client.get_orders(kwargs['params'])

        return {
            "order_data": order_data + [ecommerce_response],
        }
