"""
Filters used by the orders app
"""
from openedx_filters.tooling import OpenEdxPublicFilter


# Filter definitions create a filter pipeline; when run, the pipeline works as an extension point to delegate some
# work to other component apps. (In this PoC, though, the steps are implemented in `pipeline.py` rather than another
# app)
class OrderDataRequested(OpenEdxPublicFilter):
    """
    Filter to request order data
    """
    # This is the key for configuring the pipeline steps in the OPEN_EDX_FILTERS_CONFIG dict in `settings/base.py`
    filter_type = "org.edx.coordinator.orders.v1"

    # Although pipelines can be run using the generic `run_pipeline` method, implementing a `run_filter` method allows
    # more control, including a specific signature, default arguments, and extracting the relevant results

    @classmethod
    def run_filter(cls, request, order_data=None):
        """
        Execute the filter pipeline with the desired signature.
        """
        if order_data is None:
            order_data = []

        # build parameters
        page = request.query_params.get("page")
        page_size = request.query_params.get("page_size")
        params = {'username': request.user.username, "page": page, "page_size": page_size}

        data = super().run_pipeline(params=params, order_data=order_data)
        order_data = data.get("order_data")
        return order_data
