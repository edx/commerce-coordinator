"""
Filters for LMS
"""

from openedx_filters.tooling import OpenEdxPublicFilter


class PaymentPageRedirectRequested(OpenEdxPublicFilter):
    """
    Filter to gather payment page redirect urls.
    """
    # See pipeline step configuration OPEN_EDX_FILTERS_CONFIG dict in `settings/base.py`
    filter_type = "org.edx.coordinator.lms.payment.page.redirect.requested.v1"

    @classmethod
    def run_filter(cls, request):
        """
        Execute the filter pipeline with the desired signature.
        Arguments:
            request: django.http.HttpRequest object passed through from lms views.py
        """

        redirect_url = super().run_pipeline(request=request)

        return redirect_url


class OrderRefundRequested(OpenEdxPublicFilter):
    """
    Filter to create refund/return for Commercetools order
    """
    # See pipeline step configuration OPEN_EDX_FILTERS_CONFIG dict in `settings/base.py`
    filter_type = "org.edx.coordinator.lms.order.refund.requested.v1"

    @classmethod
    def run_filter(cls, order_id, order_line_item_id):  # pragma no cover
        """
        Call the PipelineStep(s) defined for this filter.
        Arguments:
            order_id: Order ID
            order_line_item_id: Order's line item ID
        Returns:
            order_refund: Updated order with return item attached
        """

        return super().run_pipeline(order_id=order_id, order_line_item_id=order_line_item_id)


class UserRetirementRequested(OpenEdxPublicFilter):
    """
    Filter to anonymize retired customer fields in Commercetools
    """
    # See pipeline step configuration OPEN_EDX_FILTERS_CONFIG dict in `settings/base.py`
    filter_type = "org.edx.coordinator.lms.user.retirement.requested.v1"

    @classmethod
    def run_filter(cls, lms_user_id):  # pragma no cover
        """
        Call the PipelineStep(s) defined for this filter.
        Arguments:
            lms_user_id: edx LMS user ID of customer
        Returns:
            returned_customer: Updated customer Commercetools object with anonymized fields
        """

        return super().run_pipeline(lms_user_id=lms_user_id)
