"""
Commercetools filter pipelines
"""
import attr
from openedx_filters import PipelineStep

from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient
from commerce_coordinator.apps.commercetools.data import order_from_commercetools


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

        converted_orders = [attr.asdict(order_from_commercetools(x, ct_orders[1])) for x in ct_orders[0].results]

        order_data.append(
            ct_orders[0].rebuild(converted_orders)
        )

        return {
            "order_data": order_data
        }
