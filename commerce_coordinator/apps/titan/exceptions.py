"""Customer exceptions."""
from rest_framework.exceptions import APIException


class PaymentNotFound(APIException):
    status_code = 404
    default_detail = 'Requested payment not found. Please make sure you are passing active payment number.'
    default_code = 'payment_not_found'


class PaymentMismatch(APIException):
    status_code = 409
    default_detail = 'The payment_number or order_uuid held by frontend-app-payment does not match the latest on the' \
                     ' server.'
    default_code = 'payment_mismatch'


class ProcessingAlreadyRequested(APIException):
    status_code = 409
    default_detail = 'The payment was already requested to be processed.'
    default_code = 'already_processing'


class AlreadyPaid(APIException):
    status_code = 409
    default_detail = 'The payment was already paid.'
    default_code = 'already_paid'


class InvalidOrderPayment(APIException):
    status_code = 409
    default_detail = 'Your requested payment does not belong to this payment'
    default_code = 'invalid_order_payment'


class NoActiveOrder(APIException):
    status_code = 404
    default_detail = 'The user with the specified edx_lms_user_id does not have an active order'
    default_code = 'no_active_order'
