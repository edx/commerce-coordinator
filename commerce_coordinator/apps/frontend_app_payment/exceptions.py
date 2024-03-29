"""Custom exceptions."""

from rest_framework.exceptions import APIException


class UnhandledPaymentStateAPIError(APIException):
    status_code = 422
    default_detail = 'Get Payment received a Payment State that is not handled.'
    default_code = 'unhandled_payment_state'


class TransactionDeclinedAPIError(APIException):
    status_code = 409
    default_detail = 'Transaction for the given payment has been declined'
    default_code = 'transaction-declined-message'
