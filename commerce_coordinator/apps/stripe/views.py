"""
Views for the stripe app
"""
import logging

import stripe
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from edx_django_utils.cache import TieredCache
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from commerce_coordinator.apps.core.constants import PaymentState
from commerce_coordinator.apps.core.memcache import safe_key
from commerce_coordinator.apps.rollout.utils import is_commercetools_stripe_refund, is_legacy_order
from commerce_coordinator.apps.stripe.constants import StripeEventType
from commerce_coordinator.apps.stripe.exceptions import (
    InvalidPayloadAPIError,
    SignatureVerificationAPIError,
    UnhandledStripeEventAPIError
)
from commerce_coordinator.apps.stripe.signals import payment_processed_signal, payment_refunded_signal

logger = logging.getLogger(__name__)

stripe.api_key = settings.PAYMENT_PROCESSOR_CONFIG['edx']['stripe']['secret_key']
endpoint_secret = settings.PAYMENT_PROCESSOR_CONFIG['edx']['stripe']['webhook_endpoint_secret']
source_system_identifier = settings.PAYMENT_PROCESSOR_CONFIG['edx']['stripe']['source_system_identifier']
NOTIFICATION_CACHE_TTL_SECS = 60 * 10  # 10 Mins


class SingleInvocationAPIView(APIView):
    """APIView that can mark itself as running or not running within TieredCache"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.meta_id = None
        self.meta_view = None
        self.meta_should_mark_not_running = True

    @staticmethod
    def _view_cache_key(view: str, identifier: str) -> str:
        """Get cache key for view and identifier"""
        return safe_key(key=f"{view}_{identifier}", key_prefix="ct_sub_msg_invo", version="1")

    def mark_running(self, view: str, identifier: str, tf=True):
        """Mark view as running or not running"""
        self.set_view(view)
        self.set_identifier(identifier)
        key = SingleInvocationAPIView._view_cache_key(view, identifier)

        if TieredCache.get_cached_response(key).is_found or not tf:
            try:
                TieredCache.delete_all_tiers(key)

            # not all caches throw this but a few do.
            except ValueError as _:  # pragma no cover
                # No-Op, Key not found.
                pass

        if tf:
            TieredCache.set_all_tiers(key, tf, NOTIFICATION_CACHE_TTL_SECS)

    @staticmethod
    def _is_running(view: str, identifier: str):
        """Check if view is running"""
        key = SingleInvocationAPIView._view_cache_key(view, identifier)
        cache_value = TieredCache.get_cached_response(key)
        if cache_value.is_found or cache_value.get_value_or_default(False):
            logger.debug(f'[CT-{view}] Currently processing request for %s, ignoring invocation', identifier)
            return True
        return False

    def set_view(self, view: str):
        """Set the view to mark as running"""
        self.meta_view = view

    def set_identifier(self, identifier: str):
        """Set the identifier to mark as running"""
        self.meta_id = identifier

    # Right now we DON'T want to mark the view as not running, unless error.
    # def finalize_response(self, request, response, *args, **kwargs):
    #     tag = self.meta_view
    #     identifier = self.meta_id
    #     if self.meta_should_mark_not_running:
    #         SingleInvocationAPIView.mark_running(tag, identifier, False)
    #     return super().finalize_response(request, response, *args, **kwargs)

    def handle_exception(self, exc):
        """Mark view as not running on exception"""
        tag = self.meta_view
        identifier = self.meta_id
        self.mark_running(tag, identifier, False)
        return super().handle_exception(exc)


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
    # TODO: Make this endpoint accessible for Stripe servers only.

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
        if event.type == StripeEventType.PAYMENT_SUCCESS:
            payment_state = PaymentState.COMPLETED.value
        elif event.type == StripeEventType.PAYMENT_FAILED:
            payment_state = PaymentState.FAILED.value
        elif event.type == StripeEventType.PAYMENT_REFUNDED:
            idempotency_key = event.get('request').get('idempotency_key')
            if self._is_running(tag, idempotency_key):  # pragma no cover
                self.meta_should_mark_not_running = False
                return Response(status=status.HTTP_200_OK)
            else:
                self.mark_running(tag, idempotency_key)

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
                    stripe_refund=latest_refund
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
        else:
            raise UnhandledStripeEventAPIError

        payment_intent = event.data.object

        event_source_system_identifier = payment_intent.metadata.get('source_system')
        logger.info(
            '[Stripe webhooks] event %s with amount %d and payment intent ID [%s], source: [%s].',
            event.type,
            payment_intent.amount,
            payment_intent.id,
            event_source_system_identifier,
        )

        if event_source_system_identifier != source_system_identifier:
            logger.info(
                '[Stripe webhooks] Skipping event %s with payment intent ID [%s], source: [%s].',
                event.type,
                payment_intent.id,
                event_source_system_identifier,
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
