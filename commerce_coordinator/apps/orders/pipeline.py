"""
order app filter pipeline implementations.
"""

from openedx_filters import PipelineStep

from .clients import EcommerceApiClient

# PipelineSteps augment, filter, or transform data passed into them and return a dict that gets merged into the
# `**kwargs` passed to the next step in the pipeline.  The merge is done using
# [dict.update()](https://docs.python.org/3/library/stdtypes.html#dict.update)
#
# By overriding `run_filter` and adding expected arguments to the signature, we get a small amount checking that the
# name, for example here "sample_data", was among the arguments passed in.


class AddEcommerceOrders(PipelineStep):
    """
    Adds ecommerce orders to the order data list.
    """
    def run_filter(self, order_data, *args, **kwargs):  # pylint: disable=arguments-differ

        ecommerce_api_client = EcommerceApiClient()
        ecommerce_response = ecommerce_api_client.get_orders(kwargs['params'])

        return {
            "order_data": order_data + [ecommerce_response],
        }


class AddSomeMoreData(PipelineStep):
    """
    Adds more data to the sample data list.
    """
    def run_filter(self, order_data, *args, **kwargs):  # pylint: disable=arguments-differ
        return {
            "order_data": order_data + [{"turtles": {"turtles": {"turtles": "all the way down"}}}],
        }
