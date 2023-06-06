"""Customer exceptions."""
from rest_framework.exceptions import APIException


class PaymentNotFound(APIException):
    status_code = 404
    default_detail = 'Requested payment not found. Please make sure you are passing active payment number.'
    default_code = 'payment_not_found'

class NoActiveOrder(APIException):
    status_code = 404
    default_detail = 'The user with the specified edx_lms_user_id does not have an active order'
    default_code = 'no_active_order'