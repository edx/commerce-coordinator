"""
Pipelines for paypal app
"""

import logging
from urllib.parse import urlencode

from django.conf import settings
from commerce_coordinator.apps.paypal.clients import PayPalClient
from commerce_coordinator.apps.core.constants import PipelineCommand
from openedx_filters import PipelineStep

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

        if psp != EDX_PAYPAL_PAYMENT_INTERFACE_NAME and not amount_in_cents:
            return PipelineCommand.CONTINUE.value

        if has_been_refunded:
            logger.info(f'[{tag}] payment already refunded from psp: {psp}, skipping.')
            return {
                'refund_response': "charge_already_refunded"
            }

        paypal_client = PayPalClient()
        try:
            paypal_refund_response = paypal_client.refund_order(order_id=order_id)
            return {
                'refund_response': paypal_refund_response
            }
        except Exception as ex:
            logger.info(f'[CT-{tag}] Unsuccessful PayPal refund with details:'
                        f'[order_id: {order_id}'
                        f'message_id: {kwargs["message_id"]}')
            raise Exception from ex


