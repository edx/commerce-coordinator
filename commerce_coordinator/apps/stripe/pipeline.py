"""
Pipelines for stripe app
"""

import logging

from openedx_filters import PipelineStep
from stripe.error import StripeError

from commerce_coordinator.apps.commercetools.catalog_info.constants import EDX_STRIPE_PAYMENT_INTERFACE_NAME
from commerce_coordinator.apps.core.constants import PaymentMethod, PipelineCommand
from commerce_coordinator.apps.stripe.clients import StripeAPIClient
from commerce_coordinator.apps.stripe.constants import Currency
from commerce_coordinator.apps.stripe.exceptions import StripeIntentCreateAPIError, StripeIntentUpdateAPIError
from commerce_coordinator.apps.stripe.filters import PaymentDraftCreated
from commerce_coordinator.apps.stripe.utils import convert_dollars_in_cents

logger = logging.getLogger(__name__)


class CreateOrGetStripeDraftPayment(PipelineStep):
    """
    Create or retrieve previous creation attempts of a Stripe PaymentIntent.

    Use the order number as an idempotency key so Stripe will replay responses
    for creation attempts of a PaymentIntent for the same order number in the
    last 24 hours.
    """

    def run_filter(self, order_data, edx_lms_user_id, **kwargs):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Arguments:
            order_data: any preliminary orders (from earlier pipeline step) we want to append to.
            edx_lms_user_id: the user id requesting the draft payment.
            kwargs['payment_intent_data']: optional. If present, skip this pipeline step.
            kwargs['payment_data']: optional. If present, skip this pipeline step.
        """
        if kwargs.get('payment_intent_data'):
            return PipelineCommand.HALT.value
        if kwargs.get('payment_data'):
            return PipelineCommand.HALT.value

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
            payment_intent_id=payment_intent['id'],
            client_secret=payment_intent['client_secret'],
            payment_method_name=PaymentMethod.STRIPE.value,
            provider_response_body=payment_intent,
            edx_lms_user_id=edx_lms_user_id
        )
        return {
            'payment_data': payment,
            'payment_intent_data': payment_intent,
        }


class UpdateStripePayment(PipelineStep):
    """
    Update stripe payment with the latest information.
    """

    def run_filter(
        self, edx_lms_user_id, payment_intent_id, order_uuid, payment_number, amount_in_cents, currency, **kwargs
    ):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.

        Args:
            edx_lms_user_id(int): The edx.org LMS user ID of the user making the payment.
            payment_intent_id (str): The Stripe PaymentIntent id to look up.
            order_uuid (str): The identifier of the order. There should be only
                one Stripe PaymentIntent for this identifier.
            payment_number (str): The payment number. When Stripe's
                webhook says a PaymentIntent was paid, we record this payment
                number as paid and error if it's not the latest payment.
            amount_in_cents (int): The number of cents of the order.
            currency (str): ISO currency code. Must be Stripe-supported.
            kwargs: arguments passed through from the filter.
        """

        stripe_api_client = StripeAPIClient()
        try:
            provider_response_body = stripe_api_client.update_payment_intent(
                edx_lms_user_id=edx_lms_user_id,
                payment_intent_id=payment_intent_id,
                order_uuid=order_uuid,
                current_payment_number=payment_number,
                amount_in_cents=amount_in_cents,
                currency=currency,
            )
        except StripeError as ex:
            raise StripeIntentUpdateAPIError from ex

        return {
            'provider_response_body': provider_response_body,
        }


class GetPaymentIntentReceipt(PipelineStep):
    """ Pull the receipt if the payment_intent is set """

    # pylint: disable=unused-argument
    def run_filter(self, psp=None, payment_intent_id=None, **params):
        tag = type(self).__name__

        if psp == EDX_STRIPE_PAYMENT_INTERFACE_NAME and payment_intent_id is None:
            logger.debug(f'[{tag}] payment_intent_id not set, skipping.')
            return PipelineCommand.CONTINUE.value

        if psp == EDX_STRIPE_PAYMENT_INTERFACE_NAME:
            stripe_api_client = StripeAPIClient()
            payment_intent = stripe_api_client.retrieve_payment_intent(
                payment_intent_id,
                ["latest_charge"]
            )
            receipt_url = payment_intent.latest_charge.receipt_url

            return {
                'payment_intent': payment_intent,
                'redirect_url': receipt_url
            }

        return PipelineCommand.CONTINUE.value


class RefundPaymentIntent(PipelineStep):
    """
    Refunds a payment intent
    """

    def run_filter(
        self,
        order_id,
        payment_intent_id,
        amount_in_cents,
        has_been_refunded,
        psp,
        **kwargs
    ):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Arguments:
            order_id (str): The identifier of the order.
            payment_intent_id (str): The Stripe PaymentIntent id to look up.
            amount_in_cents (decimal): Total amount to refund
            has_been_refunded (bool): Has this payment been refunded
            kwargs: arguments passed through from the filter.
        """

        tag = type(self).__name__

        if psp != EDX_STRIPE_PAYMENT_INTERFACE_NAME or not payment_intent_id or not amount_in_cents:  # pragma: no cover
            logger.info(f'[{tag}] payment_intent_id or amount_in_cents not set, skipping.')
            return PipelineCommand.CONTINUE.value

        if has_been_refunded:
            logger.info(f'[{tag}] payment_intent already refunded, skipping.')
            return {
                'refund_response': "charge_already_refunded"
            }

        stripe_api_client = StripeAPIClient()

        try:
            ret_val = stripe_api_client.refund_payment_intent(
                payment_intent_id=payment_intent_id,
                amount=amount_in_cents,
                order_uuid=order_id
            )
            return {
                'refund_response': ret_val
            }
        except StripeError as ex:  # pragma: no cover
            logger.info(f'[CT-{tag}] Unsuccessful Stripe refund with details:'
                        f'[order_id: {order_id}, payment_intent_id: {payment_intent_id}'
                        f'message_id: {kwargs["message_id"]}')

            return {
                'psp_refund_error': str(ex)
            }
