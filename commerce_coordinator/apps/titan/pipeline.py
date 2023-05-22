"""
Pipelines for Titan
"""

from openedx_filters import PipelineStep

from commerce_coordinator.apps.titan.clients import TitanAPIClient


class CreateTitanOrder(PipelineStep):
    """
    Adds titan orders to the order data list.
    """

    def run_filter(self, params, order_data):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Arguments:
            params: arguments passed through from the original order history url querystring
            order_data: any preliminary orders (from earlier pipeline step) we want to append to
        """

        titan_api_client = TitanAPIClient()
        titan_response = titan_api_client.create_order(**params)

        order_data.append(titan_response)

        return {
            "order_data": order_data
        }
