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
