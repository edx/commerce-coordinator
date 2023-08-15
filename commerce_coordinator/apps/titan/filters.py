"""
Filters used by the titan app
"""
import logging

from openedx_filters.tooling import OpenEdxPublicFilter

logger = logging.getLogger(__name__)


class PaymentSuperseded(OpenEdxPublicFilter):
    """
    Filter to supersede payment from the defined PipelineStep(s)
    """
    # See pipeline step configuration OPEN_EDX_FILTERS_CONFIG dict in `settings/base.py`
    filter_type = "org.edx.coordinator.titan.payment.superseded.v1"

    @classmethod
    def run_filter(cls, **kwargs):
        """
        Call the PipelineStep(s) defined for this filter.
        Arguments:
            kwargs (dict): Arguments passed through from the original filter.
        """
        payment = super().run_pipeline(**kwargs)
        return payment
