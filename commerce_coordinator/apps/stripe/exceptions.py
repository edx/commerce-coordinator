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
