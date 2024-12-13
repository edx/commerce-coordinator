"""
Pipelines for paypal app
"""

import logging
from urllib.parse import urlencode

from django.conf import settings
from openedx_filters import PipelineStep

from commerce_coordinator.apps.commercetools.catalog_info.constants import EDX_PAYPAL_PAYMENT_INTERFACE_NAME
from commerce_coordinator.apps.core.constants import PipelineCommand

logger = logging.getLogger(__name__)


class GetPayPalPaymentReceipt(PipelineStep):
    """ Purpare PayPal payment recipt  """

    def run_filter(self, psp=None, payment_intent_id=None, **params):

        if payment_intent_id is None or psp != EDX_PAYPAL_PAYMENT_INTERFACE_NAME:
            return PipelineCommand.CONTINUE.value

        activity_page_url = settings.PAYMENT_PROCESSOR_CONFIG['edx']['paypal']['user_activity_page_url']
        query_params = {'free_text_search': params.get('order_number')}

        redirect_url = activity_page_url + '?' + urlencode(query_params)

        return {
            'redirect_url': redirect_url,
        }
