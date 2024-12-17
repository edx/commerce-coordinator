"""
Pipelines for paypal app
"""

import logging
from urllib.parse import urlencode

from django.conf import settings
from commerce_coordinator.apps.paypal.clients import PayPalClient
from commerce_coordinator.apps.core.constants import PipelineCommand
from openedx_filters import PipelineStep
from requests import RequestException

from commerce_coordinator.apps.commercetools.catalog_info.constants import EDX_PAYPAL_PAYMENT_INTERFACE_NAME

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


class RefundPayPalPayment(PipelineStep):
    """
    Refunds a PayPal payment
    """

    def run_filter(
        self,
        order_id,
        amount_in_cents,
        has_been_refunded,
        ct_transaction_interaction_id,
        psp,
        **kwargs
    ):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Arguments:
            order_id (str): The identifier of the order.
            amount_in_cents (decimal): Total amount to refund
            has_been_refunded (bool): Has this payment been refunded
            kwargs: arguments passed through from the filter.
        """

        tag = type(self).__name__

        if psp != EDX_PAYPAL_PAYMENT_INTERFACE_NAME or not amount_in_cents or not ct_transaction_interaction_id:
            return PipelineCommand.CONTINUE.value

        if has_been_refunded:
            logger.info(f'[{tag}] payment already refunded from psp: {psp}, skipping.')
            return {
                'refund_response': "charge_already_refunded"
            }

        try:
            paypal_client = PayPalClient()
            paypal_refund_response = paypal_client.refund_order(capture_id=ct_transaction_interaction_id)
            print('\n\n\n\n\n paypal_refund_response = ', paypal_refund_response)
            return {
                'refund_response': paypal_refund_response,
            }
        except Exception as ex:
            logger.error(f'[CT-{tag}] Unsuccessful PayPal refund with details: '
                        f'[order_id: {order_id} '
                        f'message_id: {kwargs["message_id"]} '
                        f'exception: {ex}')

            raise RequestException(str(ex))


