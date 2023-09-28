"""
Commercetools filter pipelines
"""

from openedx_filters import PipelineStep

from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient


class GetCommercetoolsOrders(PipelineStep):
    """
    Adds commercetools orders to the order data list.
    """

    def run_filter(self, params, order_data):  # pylint: disable=arguments-differ
        # TODO: GRM: Implement
        """
        Execute a filter with the signature specified.
        Arguments:
            params: arguments passed through from the original order history url querystring
            order_data: any preliminary orders (from earlier pipeline step) we want to append to
        """

        ct_api_client = CommercetoolsAPIClient()
        ct_orders = ct_api_client.get_orders(params)

        order_data.append(ct_orders)

        return {
            "order_data": order_data
        }
