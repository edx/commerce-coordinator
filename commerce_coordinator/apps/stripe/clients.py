"""
API clients for Stripe.
"""
import stripe
from celery.utils.log import get_task_logger
from django.conf import settings

from commerce_coordinator.apps.core import serializers

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

    def retrieve_payment_intent(self, payment_intent_id):
        """
        Retrieve a Stripe PaymentIntent.

        Args:
            payment_intent_id (str): The Stripe PaymentIntent id to look up.

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

        try:
            stripe_response = stripe.PaymentIntent.retrieve(payment_intent_id)
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
