"""Custom exceptions."""
from rest_framework.exceptions import APIException


class InvalidOrderPayment(APIException):
    status_code = 409
    default_detail = 'Your requested payment does not belong to this payment'
    default_code = 'invalid_order_payment'


class UnexpectedPayment(APIException):
    status_code = 500
    default_detail = 'Received Unexpected payment data'
    default_code = 'unexpected_payment_details'
