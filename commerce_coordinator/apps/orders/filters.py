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
    def run_filter(cls, request, order_data=None):
        """
        Call the PipelineStep(s) defined for this filter, to gather orders and return together
        """
        if order_data is None:
            order_data = []

        # build parameters
        page = request.query_params.get("page")
        page_size = request.query_params.get("page_size")
        params = {'username': request.user.username, "page": page, "page_size": page_size}

        data = super().run_pipeline(params=params, order_data=order_data)
        return data.get("order_data")
