"""Customer exceptions."""
from rest_framework.exceptions import APIException


class PaymentNotFond(APIException):
    status_code = 404
    default_detail = 'Requested payment not found. Please make sure you are passing active payment number.'
    default_code = 'payment_not_found'
