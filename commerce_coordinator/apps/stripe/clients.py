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

        logger.info('StripeAPIClient.create_or_get_payment_intent called with '
                    f'order_uuid: [{order_uuid}], '
                    f'amount_in_cents: [{amount_in_cents}], '
                    f'currency: [{currency}].')

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

        except stripe.error.IdempotencyError:
            logger.error('StripeAPIClient.create_or_get_payment_intent threw '
                         'stripe.error.IdempotencyError with '
                         f'order_uuid: [{order_uuid}], '
                         f'amount_in_cents: [{amount_in_cents}], '
                         f'currency: [{currency}].')
            raise

        logger.debug('StripeAPIClient.create_or_get_payment_intent called for '
                     f'order_uuid: [{order_uuid}] '
                     'returned stripe_response: '
                     f'[{stripe_response}].')

        return stripe_response
