"""
Filters used by the orders app
"""
from openedx_filters.tooling import OpenEdxPublicFilter


class OrderDataRequested(OpenEdxPublicFilter):
    """
    Filter to gather order data from the defined PipelineStep(s)
    """
    # See pipeline step configuration OPEN_EDX_FILTERS_CONFIG dict in `settings/base.py`
    filter_type = "org.edx.coordinator.orders.v1"

    @classmethod
    def run_filter(cls, request, params, order_data=None):
        """
        Call the PipelineStep(s) defined for this filter, to gather orders and return together
        """
        if order_data is None:
            order_data = []

        data = super().run_pipeline(params=params, order_data=order_data)
        return data.get("order_data")
