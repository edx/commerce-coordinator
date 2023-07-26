"""
Pipelines for stripe app
"""

import logging

from openedx_filters import PipelineStep
from stripe.error import StripeError

from commerce_coordinator.apps.core.constants import PaymentMethod, PaymentState
from commerce_coordinator.apps.stripe.clients import StripeAPIClient
from commerce_coordinator.apps.stripe.constants import Currency
from commerce_coordinator.apps.stripe.exceptions import StripeIntentCreateAPIError, StripeIntentUpdateAPIError
from commerce_coordinator.apps.stripe.filters import PaymentDraftCreated
from commerce_coordinator.apps.stripe.utils import convert_dollars_in_cents

logger = logging.getLogger(__name__)


class CreateOrGetStripeDraftPayment(PipelineStep):
    """
    Adds titan orders to the order data list.
    """

    def run_filter(self, order_data, recent_payment, **kwargs):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Arguments:
            recent_payment: most recent payment from order (from earlier pipeline step).
            order_data: any preliminary orders (from earlier pipeline step) we want to append to.
            kwargs: arguments passed through from the filter.
        """
        if recent_payment and recent_payment['state'] != PaymentState.FAILED.value:
            # existing payment with any state other than failed found. No need to create new payment.
            return {
                'payment_data': recent_payment,
            }

        # In case, there was not existing payment or existing payment failed, We need to create a new payment.
        stripe_api_client = StripeAPIClient()
        try:
            payment_intent = stripe_api_client.create_payment_intent(
                order_uuid=order_data['basket_id'],
                amount_in_cents=convert_dollars_in_cents(order_data['item_total']),
                currency=Currency.USD.value,
            )
        except StripeError as ex:
            raise StripeIntentCreateAPIError from ex

        payment = PaymentDraftCreated.run_filter(
            order_uuid=order_data['basket_id'],
            response_code=payment_intent['id'],
            payment_method_name=PaymentMethod.STRIPE.value,
            provider_response_body=payment_intent,
            edx_lms_user_id=kwargs['edx_lms_user_id']
        )
        return {
            'payment_data': payment,
            'order_data': order_data,
        }


class UpdateStripeDraftPayment(PipelineStep):
    """
    Adds titan orders to the order data list.
    """

    def run_filter(self, order_data, payment_data, **kwargs):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Arguments:
            kwargs: arguments passed through from the filter.
        """

        stripe_api_client = StripeAPIClient()
        try:
            stripe_api_client.update_payment_intent(
                payment_intent_id=payment_data['key_id'],
                order_uuid=payment_data['order_uuid'],
                current_payment_number=payment_data['payment_number'],
                amount_in_cents=convert_dollars_in_cents(order_data['item_total']),
                currency=Currency.USD.value,
            )
        except StripeError as ex:
            raise StripeIntentUpdateAPIError from ex

        return {
            'payment_data': payment_data,
            'order_data': order_data,
        }
