"""
Filters used by the frontend_app_ecommerce app
"""
from openedx_filters.tooling import OpenEdxPublicFilter


class OrderReceiptRedirectionUrlRequested(OpenEdxPublicFilter):
    """
    Filter to gather order receipt redirection url from the defined PipelineStep(s)
    """

    # See pipeline step configuration OPEN_EDX_FILTERS_CONFIG dict in `settings/base.py`
    filter_type = "org.edx.coordinator.frontend_app_ecommerce.order.receipt_url.requested.v1"

    @classmethod
    def run_filter(cls, params, order_number):
        """
        Filter to gather order receipt redirection url from the defined PipelineStep(s)
        """

        pipeline_data = super().run_pipeline(params=params, order_number=order_number)

        if 'redirect_url' in pipeline_data:
            return pipeline_data['redirect_url']

        # This shouldn't happen...
        return None  # pragma no cover


class OrderHistoryRequested(OpenEdxPublicFilter):
    """
    Filter to gather order data from the defined PipelineStep(s)
    """
    # See pipeline step configuration OPEN_EDX_FILTERS_CONFIG dict in `settings/base.py`
    filter_type = "org.edx.coordinator.frontend_app_ecommerce.order.history.requested.v1"

    @classmethod
    def run_filter(cls, request, params, order_data=None):
        """
        Call the PipelineStep(s) defined for this filter, to gather orders and return together
        Arguments:
            request: request object passed through from the lms filter
            params: arguments passed through from the original order history url querystring
            order_data: any preliminary orders we want to append to when running the pipeline
        """
        if order_data is None:  # pragma: no cover
            order_data = []

        pipeline_data = super().run_pipeline(request=request, params=params, order_data=order_data)
        result = pipeline_data.get("order_data")

        # Note: OpenEdxPublicFilter run_pipeline returns an array with our dictionary inside
        return result
