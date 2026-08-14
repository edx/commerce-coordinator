"""
Views for the stripe app
"""
import logging

import stripe
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from commerce_coordinator.apps.core.constants import PaymentState
from commerce_coordinator.apps.core.views import SingleInvocationAPIView
from commerce_coordinator.apps.rollout.utils import is_commercetools_stripe_refund, is_legacy_order
from commerce_coordinator.apps.stripe.constants import StripeEventType
from commerce_coordinator.apps.stripe.exceptions import (
    InvalidPayloadAPIError,
    SignatureVerificationAPIError,
    UnhandledStripeEventAPIError
)
from commerce_coordinator.apps.stripe.signals import (
    payment_processed_signal,
    payment_refunded_signal,
    payment_succeeded_commercetools_signal
)

logger = logging.getLogger(__name__)

stripe.api_key = settings.PAYMENT_PROCESSOR_CONFIG['edx']['stripe']['secret_key']
endpoint_secret = settings.PAYMENT_PROCESSOR_CONFIG['edx']['stripe']['webhook_endpoint_secret']
source_system_identifier = settings.PAYMENT_PROCESSOR_CONFIG['edx']['stripe']['source_system_identifier']


class WebhookView(SingleInvocationAPIView):
    """
    Endpoint for Stripe webhook events. A 200 response should be returned as soon as possible
    since Stripe will retry the event if no response is received.

    Django's default cross-site request forgery (CSRF) protection is disabled,
    request are verified instead by the presence of request headers STRIPE_SIGNATURE.
    This endpoint is a public endpoint however it should be used for Stripe servers only.
    """
    http_method_names = ['post']  # accept POST request only
    authentication_classes = []
    permission_classes = [AllowAny]

    @csrf_exempt
    def post(self, request):
        """Webhook entry point."""
        tag = type(self).__name__
        payload = request.body
        sig_header = request.META['HTTP_STRIPE_SIGNATURE']

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        except ValueError as e:
            logger.exception('StripeWebhooksView failed with %s', e)
            raise InvalidPayloadAPIError from e
        except stripe.error.SignatureVerificationError as e:
            logger.exception('StripeWebhooksView SignatureVerificationError: %s', e)
            raise SignatureVerificationAPIError from e

        # Handle the event
        if event.type in (StripeEventType.PAYMENT_SUCCESS, StripeEventType.PAYMENT_FAILED):
            payment_intent = event.data.object
            event_source_system = payment_intent.metadata.get('source_system')

            if event_source_system == 'commercetools':
                return self._handle_commercetools_payment_event(tag, event, payment_intent)

            return self._handle_legacy_payment_event(event, payment_intent, event_source_system, payload)

        if event.type == StripeEventType.PAYMENT_REFUNDED:
            return self._handle_refund_event(tag, event)

        raise UnhandledStripeEventAPIError

    def _handle_commercetools_payment_event(self, tag, event, payment_intent):
        """Route CommerceTools-originated PaymentIntents (UPI) to the async finalize path."""
        if event.type != StripeEventType.PAYMENT_SUCCESS:
            logger.info(
                '[Stripe webhooks] CT payment_intent.payment_failed for PI [%s], ignoring',
                payment_intent.id,
            )
            return Response(status=status.HTTP_200_OK)

        if self._is_running(tag, payment_intent.id):  # pragma no cover
            self.meta_should_mark_not_running = False
            return Response(status=status.HTTP_200_OK)

        self.mark_running(tag, payment_intent.id)

        logger.info(
            '[Stripe webhooks] CT payment_intent.succeeded for PI [%s]',
            payment_intent.id,
        )

        payment_succeeded_commercetools_signal.send_robust(
            sender=self.__class__,
            payment_intent_id=payment_intent.id,
        )
        return Response(status=status.HTTP_200_OK)

    def _handle_legacy_payment_event(self, event, payment_intent, event_source_system, payload):
        """Route legacy edX ecommerce PaymentIntents to the existing processed signal."""
        if event.type == StripeEventType.PAYMENT_SUCCESS:
            payment_state = PaymentState.COMPLETED.value
        else:
            payment_state = PaymentState.FAILED.value

        logger.info(
            '[Stripe webhooks] event %s with amount %d and payment intent ID [%s], source: [%s].',
            event.type,
            payment_intent.amount,
            payment_intent.id,
            event_source_system,
        )

        if event_source_system != source_system_identifier:
            logger.info(
                '[Stripe webhooks] Skipping event %s with payment intent ID [%s], source: [%s].',
                event.type,
                payment_intent.id,
                event_source_system,
            )
            return Response(status=status.HTTP_200_OK)

        payment_processed_signal.send_robust(
            sender=self.__class__,
            edx_lms_user_id=payment_intent.metadata.edx_lms_user_id,
            order_uuid=payment_intent.metadata.order_number,
            payment_number=payment_intent.metadata.payment_number,
            payment_state=payment_state,
            reference_number=payment_intent.id,
            amount_in_cents=payment_intent.amount,
            currency=payment_intent.currency,
            provider_response_body=payload,
        )
        return Response(status=status.HTTP_200_OK)

    def _handle_refund_event(self, tag, event):
        """Route Commercetools refunds to the refund signal, skipping legacy orders."""
        request = event.get('request') or {}
        idempotency_key = request.get('idempotency_key') if hasattr(request, 'get') else None
        # Stripe request.idempotency_key can be null; fall back to event.id so
        # unrelated refunds do not collide on a shared None cache key.
        invocation_key = idempotency_key or event.get('id') or getattr(event, 'id', None)
        if self._is_running(tag, invocation_key):  # pragma no cover
            self.meta_should_mark_not_running = False
            return Response(status=status.HTTP_200_OK)

        self.mark_running(tag, invocation_key)

        event_object = event.data.object
        order_number = event_object.metadata.order_number
        is_legacy_order_check = is_legacy_order(order_number)
        is_ct_order_check = is_commercetools_stripe_refund(event_object.metadata.get('source_system'))
        payment_intent_id = event_object.payment_intent

        if not is_legacy_order_check and is_ct_order_check:
            event_source_system_identifier = event_object.metadata.get('source_system')
            refunds = event_object.refunds.data
            latest_refund = max(refunds, key=lambda refund: refund['created'])

            logger.info(
                '[Stripe webhooks] refund event %s with payment intent ID [%s] '
                'and order number [%s], source: [%s].',
                event.type,
                payment_intent_id,
                order_number,
                event_source_system_identifier,
            )

            payment_refunded_signal.send_robust(
                sender=self.__class__,
                payment_intent_id=payment_intent_id,
                stripe_refund=latest_refund,
                order_number=order_number,
            )
        else:
            logger.info(
                '[Stripe webhooks] skipping refund event %s with payment intent ID [%s] '
                'and order number [%s], as it is not a Commercetools order.',
                event.type,
                payment_intent_id,
                order_number,
            )
        return Response(status=status.HTTP_200_OK)
