"""
Legacy filter pipeline implementation
"""

from django.conf import settings
from openedx_filters import PipelineStep

from commerce_coordinator.apps.core.constants import PipelineCommand
from commerce_coordinator.apps.frontend_app_payment.constants import FRONTEND_APP_PAYMENT_CHECKOUT


class GetPaymentMFERedirectUrl(PipelineStep):
    """
    Generates legacy redirect url
    """
    def run_filter(self, active_order_management_system, request, redirect_url=None):
        # pylint: disable=arguments-differ, unused-argument
        if active_order_management_system == FRONTEND_APP_PAYMENT_CHECKOUT:
            return {
                "redirect_url": settings.FRONTEND_APP_PAYMENT_URL
            }
        else:
            return PipelineCommand.CONTINUE.value
