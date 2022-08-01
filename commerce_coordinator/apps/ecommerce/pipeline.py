"""
Ecommerce filter pipelines
"""

from openedx_filters import PipelineStep

from commerce_coordinator.apps.ecommerce.clients import EcommerceApiClient


class GetEcommerceOrders(PipelineStep):
    """
    Adds ecommerce orders to the order data list.
    """

    def run_filter(self, order_data, **kwargs):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Arguments:
            order_data: eventually this filter will collect from multiple pipeline steps
            We'll add any new order data to those previous results and return the whole set together
            kwargs: we override run_filter to check that expected arguments are passed in
        """

        ecommerce_api_client = EcommerceApiClient()
        ecommerce_response = ecommerce_api_client.get_orders(kwargs['params'])

        return {
            "order_data": order_data + [ecommerce_response],
        }
