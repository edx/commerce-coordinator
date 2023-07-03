"""
API clients for Stripe.
"""
import stripe
from celery.utils.log import get_task_logger
from django.conf import settings

# Use special Celery logger for tasks client calls.
logger = get_task_logger(__name__)


class StripeAPIClient:
    """
    API client for calls to Stripe using API key.
    """

    def __init__(self):
        configuration = settings.PAYMENT_PROCESSOR_CONFIG['edx']['stripe']

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

        logger.info('StripeAPIClient.create_payment_intent called with '
                    f'order_uuid: [{order_uuid}], '
                    f'amount_in_cents: [{amount_in_cents}], '
                    f'currency: [{currency}].')

        if not order_uuid or not amount_in_cents or not currency:
            raise ValueError('Missing parameter or amount_in_cents is zero.')

        if not isinstance(amount_in_cents, int) or not amount_in_cents > 0:
            raise ValueError('amount_in_cents must be a positive, non-zero int.')

        try:
            stripe_response = stripe.PaymentIntent.create(
                amount=amount_in_cents,
                currency=currency,
                description=order_uuid,
                metadata={
                    'order_number': order_uuid,
                    'source_system': 'edx/commerce_coordinator?v=1',
                },
                # Disallow confirmation from client for server-side embargo check.
                secret_key_confirmation='required',
                # Don't create a new intent for the same order_number.
                idempotency_key=f'order_number_pi_create_v1_{order_uuid}',
            )
        except stripe.error.IdempotencyError as exc:
            logger.error('StripeAPIClient.create_payment_intent threw '
                         f'[{exc}] with '
                         f'order_uuid: [{order_uuid}], '
                         f'amount_in_cents: [{amount_in_cents}], '
                         f'currency: [{currency}].')
            # TODO: In the future, we might expect IdempotencyError as a normal
            # part of our users' flows. For example: in our legacy ecommerce
            # repo, we avoid a request to the database to see if an order
            # already has a Stripe PaymentIntent. Either: (a) Remove this block
            # if this assumption is no longer the case. IdempotencyErrors will
            # be caught anyways by the stripe.error.StripeError exception
            # handler below. Or: (b) Remove the raise & implement expected
            # behavior here.
            raise
        except stripe.error.StripeError as exc:
            logger.error('StripeAPIClient.create_payment_intent threw '
                         f'[{exc}] with '
                         f'order_uuid: [{order_uuid}], '
                         f'amount_in_cents: [{amount_in_cents}], '
                         f'currency: [{currency}].')
            raise

        logger.debug('StripeAPIClient.create_payment_intent called with '
                     f'order_uuid: [{order_uuid}] '
                     f'amount_in_cents: [{amount_in_cents}], '
                     f'currency: [{currency}] '
                     'returned stripe_response: '
                     f'[{stripe_response}].')

        return stripe_response

    def retrieve_payment_intent(self, payment_intent_id):
        """
        Retrieve a Stripe PaymentIntent.

        Args:
            order_uuid (str): The Stripe PaymentIntent id to look up.

        Returns:
            The response from Stripe.

        See:
            https://stripe.com/docs/api/payment_intents/retrieve
        """

        logger.info('StripeAPIClient.retrieve_payment_intent called with '
                    f'payment_intent_id: [{payment_intent_id}].')

        try:
            stripe_response = stripe.PaymentIntent.retrieve(payment_intent_id)
        except stripe.error.StripeError as exc:
            logger.error('StripeAPIClient.retrieve_payment_intent threw '
                         f'[{exc}] with '
                         f'payment_intent_id: [{payment_intent_id}].')
            raise

        logger.debug('StripeAPIClient.retrieve_payment_intent called with '
                     f'payment_intent_id: [{payment_intent_id}], '
                     'returned stripe_response: '
                     f'[{stripe_response}].')

        return stripe_response
