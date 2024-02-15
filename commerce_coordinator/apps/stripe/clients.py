"""
API clients for Stripe.
"""

import stripe
from celery.utils.log import get_task_logger
from django.conf import settings

from commerce_coordinator.apps.core import serializers
from commerce_coordinator.apps.stripe.constants import StripeRefundStatus

# Use special Celery logger for tasks client calls.
logger = get_task_logger(__name__)


class StripeAPIClient:
    """
    API client for calls to Stripe using API key.
    """

    def __init__(self):
        configuration = settings.PAYMENT_PROCESSOR_CONFIG['edx']['stripe']
        # Add the following string to the metadata of updated or created PaymentIntents.
        self.source_system_identifier = configuration['source_system_identifier']
        # The secret API key used by the backend to communicate with Stripe. Private/secret.
        stripe.api_key = configuration['secret_key']
        # Stripe API version to use. Will use latest allowed in Stripe Dashboard if None.
        stripe.api_version = configuration['api_version']
        # Send anonymous latency metrics to Stripe.
        stripe.enable_telemetry = configuration['enable_telemetry']
        # Stripe client logging level. None will default to INFO.
        stripe.log = configuration['log_level']
        # How many times to automatically retry requests. None means no retries.
        stripe.max_network_retries = configuration['max_network_retries']
        # Send requests somewhere else instead of Stripe. May be useful for testing.
        stripe.proxy = configuration['proxy']

    def create_payment_intent(self, order_uuid, amount_in_cents, currency):
        """
        Create a Stripe PaymentIntent.

        Args:
            order_uuid (str): The identifier of the order. There should be only
                one Stripe PaymentIntent for this identifier.
            amount_in_cents (int): The number of cents of the order.
            currency (str): ISO currency code. Must be Stripe-supported.

        Returns:
            The response from Stripe.

        Raises:
            IdempotencyError: A PaymentIntent has already been created for this
                order with a different amount_in_cents or currency.

        See:
            https://stripe.com/docs/api/payment_intents/create
        """
        # Save arguments.
        initial_locals = dict(locals())
        del initial_locals['self']

        logger.info('StripeAPIClient.create_payment_intent called with '
                    f'args: [{initial_locals}].')

        class CreatePaymentIntentInputSerializer(serializers.CoordinatorSerializer):
            '''Serializer for StripeAPIClient.create_payment_intent'''
            order_uuid = serializers.UUIDField()
            amount_in_cents = serializers.IntegerField(min_value=1)
            currency = serializers.CharField(min_length=3, max_length=3)

        CreatePaymentIntentInputSerializer(data=initial_locals).is_valid(raise_exception=True)

        try:
            stripe_response = stripe.PaymentIntent.create(
                amount=amount_in_cents,
                currency=currency,
                description=order_uuid,
                metadata={
                    'order_number': order_uuid,
                    'source_system': self.source_system_identifier,
                },
                # Disallow confirmation from client for server-side embargo check.
                secret_key_confirmation='required',
                # Don't create a new intent for the same order_number.
                idempotency_key=f'order_number_pi_create_v1_{order_uuid}',
            )
            logger.debug('StripeAPIClient.create_payment_intent called with '
                         f'args: [{initial_locals}] '
                         'returned stripe_response: '
                         f'[{stripe_response}].')
            logger.info('StripeAPIClient.create_payment_intent called with '
                        f'args: [{initial_locals}] '
                        'created payment intent id: '
                        f'[{stripe_response.id}].')
        except stripe.error.StripeError as exc:
            logger.error('StripeAPIClient.create_payment_intent threw '
                         f'[{exc}] with '
                         f'args: [{initial_locals}].')
            raise

        return stripe_response

    def retrieve_payment_intent(self, payment_intent_id, expand = None):
        """
        Retrieve a Stripe PaymentIntent.

        Args:
            payment_intent_id (str): The Stripe PaymentIntent id to look up.
            expand (List[str] or None): The list of payment intent fields to exapnd

        Returns:
            The response from Stripe.

        See:
            https://stripe.com/docs/api/payment_intents/retrieve
        """
        # Save arguments.
        initial_locals = dict(locals())
        del initial_locals['self']

        logger.info('StripeAPIClient.retrieve_payment_intent called with '
                    f'args: [{initial_locals}].')

        class RetrievePaymentIntentInputSerializer(serializers.CoordinatorSerializer):
            '''Serializer for StripeAPIClient.retrieve_payment_intent.'''
            payment_intent_id = serializers.CharField()

        RetrievePaymentIntentInputSerializer(data=initial_locals).is_valid(raise_exception=True)

        expand_params = [] if not expand else expand

        try:
            stripe_response = stripe.PaymentIntent.retrieve(payment_intent_id, expand=expand_params)
            logger.debug('StripeAPIClient.retrieve_payment_intent called with '
                         f'args: [{initial_locals}] '
                         'returned stripe_response: '
                         f'[{stripe_response}].')
            logger.info('StripeAPIClient.retrieve_payment_intent called with '
                        f'args: [{initial_locals}] '
                        f'retrieived payment intent id: [{stripe_response.id}].')
        except stripe.error.StripeError as exc:
            logger.error('StripeAPIClient.retrieve_payment_intent threw '
                         f'[{exc}] with '
                         f'args: [{initial_locals}].')
            raise

        return stripe_response

    def update_payment_intent(
        self,
        edx_lms_user_id,
        payment_intent_id,
        order_uuid,
        current_payment_number,
        amount_in_cents,
        currency,
    ):
        """
        Update a Stripe PaymentIntent.

        Args:
            edx_lms_user_id(int): The edx.org LMS user ID of the user making the payment.
            payment_intent_id (str): The Stripe PaymentIntent id to look up.
            order_uuid (str): The identifier of the order. There should be only
                one Stripe PaymentIntent for this identifier.
            current_payment_number (str): The payment number. When Stripe's
                webhook says a PaymentIntent was paid, we record this payment
                number as paid and error if it's not the latest payment.
            amount_in_cents (int): The number of cents of the order.
            currency (str): ISO currency code. Must be Stripe-supported.

        Returns:
            The response from Stripe.

        See:
            https://stripe.com/docs/api/payment_intents/update
        """
        # Save arguments.
        initial_locals = dict(locals())
        del initial_locals['self']

        logger.info('StripeAPIClient.update_payment_intent called with '
                    f'args: [{initial_locals}].')

        class UpdatePaymentIntentInputSerializer(serializers.CoordinatorSerializer):
            '''Serializer for StripeAPIClient.update_payment_intent.'''
            edx_lms_user_id = serializers.IntegerField(allow_null=False)
            payment_intent_id = serializers.CharField()
            order_uuid = serializers.UUIDField()
            current_payment_number = serializers.CharField()
            amount_in_cents = serializers.IntegerField(min_value=1)
            currency = serializers.CharField(min_length=3, max_length=3)

        UpdatePaymentIntentInputSerializer(data=initial_locals).is_valid(raise_exception=True)

        try:
            stripe_response = stripe.PaymentIntent.modify(
                payment_intent_id,
                amount=amount_in_cents,
                currency=currency,
                description=order_uuid,
                metadata={
                    'edx_lms_user_id': edx_lms_user_id,
                    'order_number': order_uuid,
                    'payment_number': current_payment_number,
                    'source_system': self.source_system_identifier,
                },
            )
            logger.debug('StripeAPIClient.update_payment_intent called with '
                         f'args: [{initial_locals}] '
                         'returned stripe_response: '
                         f'[{stripe_response}].')
            logger.info('StripeAPIClient.update_payment_intent called with '
                        f'args: [{initial_locals}] '
                        'updated payment intent id: '
                        f'[{stripe_response.id}].')
        except stripe.error.StripeError as exc:
            logger.error('StripeAPIClient.update_payment_intent threw '
                         f'[{exc}] with '
                         f'args: [{initial_locals}].')
            raise

        return stripe_response

    def confirm_payment_intent(
        self,
        payment_intent_id,
    ):
        """
        Confirm a Stripe PaymentIntent.

        Args:
            payment_intent_id (str): The Stripe PaymentIntent id to look up.

        Returns:
            The response from Stripe.

        See:
            https://stripe.com/docs/api/payment_intents/confirm
        """

        try:
            confirm_api_response = stripe.PaymentIntent.confirm(
                payment_intent_id,
                # stop on complicated payments MFE can't handle yet
                error_on_requires_action=True,
                expand=['payment_method'],
            )
            logger.debug('StripeAPIClient.confirm_payment_intent called with '
                         f'payment_intent_id: {payment_intent_id} '
                         'returned stripe_response: '
                         f'[{confirm_api_response}].')
        except stripe.error.StripeError as exc:
            logger.exception('StripeAPIClient.confirm_payment_intent threw '
                             f'[{exc}] with '
                             f'payment_intent_id: {payment_intent_id}.')
            raise

        return confirm_api_response

    def refund_payment_intent(
            self,
            order_uuid,
            payment_intent_id,
            amount
    ):
        """
        Issues Stripe refund for desired order.

        Args:
            order_uuid (str): The identifier of the order.
            payment_intent_id (str): The Stripe PaymentIntent id to look up.
            amount (decimal): The amount to refund.

        Returns:
            The identifier of refund response from Stripe.

        See:
            https://stripe.com/docs/api/refunds/create
        """
        try:
            # Stripe requires amount to be in cents. "amount" is a Decimal object to the hundredths place
            amount_in_cents = int(amount * 100)
            refund = stripe.Refund.create(payment_intent=payment_intent_id, amount=amount_in_cents)
        except stripe.error.InvalidRequestError as err:
            if err.code == 'charge_already_refunded':
                refund = stripe.Refund.list(payment_intent=payment_intent_id, limit=1)['data'][0]
                msg = 'Skipping issuing credit (via Stripe) for order [{}] because charge was already refunded.'.format(
                    order_uuid)
                logger.warning(msg)
            else:
                msg = 'An error occurred while attempting to issue a credit (via Stripe) for order [{}].'.format(
                    order_uuid)
                logger.exception(msg)
                raise err
        except Exception as err:
            msg = 'An error occurred while attempting to issue a credit (via Stripe) for order [{}].'.format(
                order_uuid)
            logger.exception(msg)
            raise err

        if refund.status != StripeRefundStatus.REFUND_SUCCESS:
            logger.exception('Refund for order [%s] was unsuccessful', order_uuid)
            return None

        return refund.id
