from openedx_filters.tooling import OpenEdxPublicFilter


class OrderRefundRequested(OpenEdxPublicFilter):
    """
    Filter to create refund/return for Commercetools order
    """
    # See pipeline step configuration OPEN_EDX_FILTERS_CONFIG dict in `settings/base.py`
    filter_type = "org.edx.coordinator.commercetools.order.refund.requested.v1"

    @classmethod
    def run_filter(cls, order_number, **kwargs):
        # TODO: Filter will be called in SONIC-83
        """
        Call the PipelineStep(s) defined for this filter.
        Arguments:
            order_number: Order number (for now this is an order.id, but this should change in the future)
            TODO: SONIC-277 (in-progress)
        Returns:
            order_refund: Updated order with return item attached
        """

        order_refund = super().run_pipeline(order_number=order_number, **kwargs)
        return order_refund
