"""Custom exceptions."""

from rest_framework.exceptions import APIException


class SignatureVerificationAPIError(APIException):
    status_code = 403
    default_detail = 'Invalid Stripe signature'
    default_code = 'invalid_signature'


class InvalidPayloadAPIError(APIException):
    status_code = 400
    default_detail = 'Invalid Stripe payload'
    default_code = 'invalid_payload'


class UnhandledStripeEventAPIError(APIException):
    status_code = 422
    default_detail = 'Webhook received a Stripe event that is not handled.'
    default_code = 'unhandled_stripe_event'


class StripeWebhookDispatchAPIError(APIException):
    status_code = 503
    default_detail = 'Failed to enqueue Stripe webhook handler.'
    default_code = 'stripe_webhook_dispatch_error'


class StripeIntentCreateAPIError(APIException):
    status_code = 502
    default_detail = 'Error while creating payment intent on payment gateway.'
    default_code = 'stripe_intent_create_error'


class StripeIntentUpdateAPIError(APIException):
    status_code = 502
    default_detail = 'Error while updating payment intent on payment gateway.'
    default_code = 'stripe_intent_updated_error'


class StripeIntentConfirmAPIError(APIException):
    status_code = 502
    default_detail = 'Error while confirming payment intent on payment gateway.'
    default_code = 'stripe_intent_confirm_error'


class StripeIntentRefundAPIError(APIException):
    status_code = 502
    default_detail = 'Error while refunding payment intent on payment gateway.'
    default_code = 'stripe_intent_refund_error'
