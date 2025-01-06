"""Commercetools filters"""
from openedx_filters.tooling import OpenEdxPublicFilter


class OrderRefundRequested(OpenEdxPublicFilter):
    """
    Filter to create refund/return for Commercetools order
    """
    # See pipeline step configuration OPEN_EDX_FILTERS_CONFIG dict in `settings/base.py`
    filter_type = "org.edx.coordinator.commercetools.order.refund.requested.v1"

    @classmethod
    def run_filter(
        cls,
        order_id,
        return_line_item_return_id,
        return_line_item_id,
        message_id
    ):
        """
        Call the PipelineStep(s) defined for this filter.
        Arguments:
            order_id: Order ID
            return_line_item_return_id: Return line item's return ID
        Returns:
            order_refund: Updated order with return item attached
        """
        return super().run_pipeline(order_id=order_id,
                                    return_line_item_return_id=return_line_item_return_id,
                                    return_line_item_id=return_line_item_id,
                                    message_id=message_id)
