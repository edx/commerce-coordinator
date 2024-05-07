"""Commercetools filters"""
from openedx_filters.tooling import OpenEdxPublicFilter


class OrderRefundRequested(OpenEdxPublicFilter):
    """
    Filter to create refund/return for Commercetools order
    """
    # See pipeline step configuration OPEN_EDX_FILTERS_CONFIG dict in `settings/base.py`
    filter_type = "org.edx.coordinator.commercetools.order.refund.requested.v1"

    @classmethod
    def run_filter(cls, order_id, **kwargs):
        """
        Call the PipelineStep(s) defined for this filter.
        Arguments:
            order_id: Order ID
        Returns:
            order_refund: Updated order with return item attached
        """

        return super().run_pipeline(order_id=order_id, **kwargs)
