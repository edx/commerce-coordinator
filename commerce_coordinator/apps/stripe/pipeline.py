"""
Pipelines for stripe app
"""

import logging

from openedx_filters import PipelineStep
from stripe.error import StripeError

from commerce_coordinator.apps.core.constants import PaymentMethod, PaymentState
from commerce_coordinator.apps.stripe.clients import StripeAPIClient
from commerce_coordinator.apps.stripe.constants import Currency
from commerce_coordinator.apps.stripe.exceptions import (
    StripeIntentConfirmAPIError,
    StripeIntentCreateAPIError,
    StripeIntentRetrieveAPIError,
    StripeIntentUpdateAPIError
)
from commerce_coordinator.apps.stripe.filters import PaymentDraftCreated
from commerce_coordinator.apps.stripe.utils import convert_dollars_in_cents

logger = logging.getLogger(__name__)


class CreateOrGetStripeDraftPayment(PipelineStep):
    """
    Adds titan orders to the order data list.
    """

    def run_filter(self, order_data, recent_payment, edx_lms_user_id, **kwargs):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Arguments:
            recent_payment: most recent payment from order (from earlier pipeline step).
            order_data: any preliminary orders (from earlier pipeline step) we want to append to.
            edx_lms_user_id: the user id requesting the draft payment.
        """

        if recent_payment and recent_payment['state'] != PaymentState.FAILED.value:
            # NOTE: GRM: I DONT THINK WE CAN LEAVE HERE LIKE THIS. WE NEED THE CLIENT SECRET...
            #            IS IT EXPECTED TO BE STORED?

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


class GetStripeDraftPayment(PipelineStep):
    """
    Retrieve a PaymentIntent from Stripe.
    """

    def run_filter(self, payment_data, **kwargs):  # pylint: disable=arguments-differ
        """
        Executes a filter with the signature specified.

        Args:
            payment_data (dict): The payment object.
        """
        # Skip talking to Stripe if payment_intent_data is already populated.
        if kwargs.get('payment_intent_data'):
            return {}  # Keep pipeline unchanged.

        payment_intent_id = payment_data['key_id']

        stripe_api_client = StripeAPIClient()
        try:
            payment_intent = stripe_api_client.retrieve_payment_intent(payment_intent_id)
        except StripeError as ex:
            raise StripeIntentRetrieveAPIError from ex

        # TODO: THES-260: Fix mixup of key_id and client_secret
        payment_data['key_id'] = payment_intent['client_secret']

        return {
            'payment_data': payment_data,
            'payment_intent_data': payment_intent,
        }


class UpdateStripeDraftPayment(PipelineStep):
    """
    Adds titan orders to the order data list.
    """

    def run_filter(self, edx_lms_user_id, order_data, payment_data, **kwargs):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Arguments:
            kwargs: arguments passed through from the filter.
        """

        stripe_api_client = StripeAPIClient()
        try:
            payment_intent = stripe_api_client.update_payment_intent(
                edx_lms_user_id=edx_lms_user_id,
                payment_intent_id=payment_data['key_id'],
                order_uuid=payment_data['order_uuid'],
                current_payment_number=payment_data['payment_number'],
                amount_in_cents=convert_dollars_in_cents(order_data['item_total']),
                currency=Currency.USD.value,
            )
        except StripeError as ex:
            raise StripeIntentUpdateAPIError from ex

        return {
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
        Arguments:
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


class ConfirmPayment(PipelineStep):
    """
    Adds titan orders to the order data list.
    """

    def run_filter(self, payment_data, **kwargs):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Arguments:
            kwargs: arguments passed through from the filter.
        """

        stripe_api_client = StripeAPIClient()
        try:
            payment_intent = stripe_api_client.confirm_payment_intent(
                payment_intent_id=payment_data['key_id'],
            )
        except StripeError as ex:
            raise StripeIntentConfirmAPIError from ex

        return {
            'payment_intent_data': payment_intent,
        }
