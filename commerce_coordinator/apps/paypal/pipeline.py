"""
Pipelines for paypal app
"""

import logging
from urllib.parse import urlencode, urljoin

from django.conf import settings
from openedx_filters import PipelineStep

from commerce_coordinator.apps.commercetools.catalog_info.constants import EDX_PAYPAL_PAYMENT_INTERFACE_NAME

logger = logging.getLogger(__name__)


class GetPayPalPaymentReceipt(PipelineStep):
    """ Purpare PayPal payment recipt  """

    def run_filter(self, psp=None, **params):
        if psp == EDX_PAYPAL_PAYMENT_INTERFACE_NAME:
            base_url = settings.PAYPAL_BASE_URL
            activities_url = settings.PAYPAL_USER_ACTIVITES_URL
            query_params = {'free_text_search': params.get('order_number')}

            redirect_url = urljoin(base_url, activities_url) + '?' + urlencode(query_params)

            return {
                'redirect_url': redirect_url,
            }

        return None
