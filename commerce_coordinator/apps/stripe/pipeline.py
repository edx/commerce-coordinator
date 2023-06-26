"""
Pipelines for stripe app
"""

import logging

from openedx_filters import PipelineStep
from stripe.error import StripeError

from commerce_coordinator.apps.core.constants import PaymentMethod, PaymentState
from commerce_coordinator.apps.stripe.clients import StripeAPIClient
from commerce_coordinator.apps.stripe.constants import Currency
from commerce_coordinator.apps.stripe.exceptions import StripeIntentCreateAPIError
from commerce_coordinator.apps.stripe.filters import PaymentDraftCreated

logger = logging.getLogger(__name__)


class CreateOrGetStripeDraftPayment(PipelineStep):
    """
    Adds titan orders to the order data list.
    """

    def run_filter(self, order_data, **kwargs):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Arguments:
            order_data: any preliminary orders (from earlier pipeline step) we want to append to.
            kwargs: arguments passed through from the filter.
        """
        payments = order_data['payments']
        if payments:
            recent_payment = payments[0]
            if recent_payment['state'] != PaymentState.FAILED.value:
                # existing payment (Draft, Processing or Paid) found. No need to create new payment.
                return {
                    'payment_data': recent_payment,
                }

        # In case, there was not existing payment or existing payment failed, We need to create a new payment.
        stripe_api_client = StripeAPIClient()
        try:
            payment_intent = stripe_api_client.create_payment_intent(
                order_uuid=order_data['basket_id'],
                amount_in_cents=order_data['item_total'],
                currency=Currency.USD.value,
            )
        except StripeError as ex:
            raise StripeIntentCreateAPIError from ex

        payment = PaymentDraftCreated.run_filter(
            order_uuid=order_data['basket_id'],
            response_code=payment_intent['id'],
            payment_method_name=PaymentMethod.STRIPE.value,
            provider_response_body=payment_intent,
        )
        return {
            'payment_data': payment,
        }
