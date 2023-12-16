"""
Commercetools filter pipeline implementation
"""

from django.conf import settings
from openedx_filters import PipelineStep

from commerce_coordinator.apps.commercetools_frontend.constants import COMMERCETOOLS_FRONTEND
from commerce_coordinator.apps.core.constants import PipelineCommand


class GetCommercetoolsRedirectUrl(PipelineStep):
    """
    Generates Commercetools redirect url
    """

    def run_filter(self, active_order_management_system, request):
        if active_order_management_system == COMMERCETOOLS_FRONTEND:
            return {
                'redirect_url': settings.COMMERCETOOLS_FRONTEND_URL
            }
        return PipelineCommand.CONTINUE.value
