"""
Views for the frontend_app_payment app
"""
import logging

from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from commerce_coordinator.apps.core.cache import PaymentCache
from commerce_coordinator.apps.core.constants import PaymentState
from commerce_coordinator.apps.frontend_app_payment.exceptions import (
    TransactionDeclinedAPIError,
    UnhandledPaymentStateAPIError
)
from commerce_coordinator.apps.titan.exceptions import NoActiveOrder

from ..stripe.constants import StripeErrorCode
from .filters import ActiveOrderRequested, DraftPaymentRequested, PaymentProcessingRequested, PaymentRequested
from .serializers import (
    DraftPaymentCreateViewInputSerializer,
    GetActiveOrderInputSerializer,
    GetPaymentInputSerializer,
    GetPaymentOutputSerializer,
    PaymentProcessInputSerializer
)

logger = logging.getLogger(__name__)


class PaymentGetView(APIView):
    """Get Payment View"""
    authentication_classes = (JwtAuthentication,)
    permission_classes = (IsAuthenticated,)
    throttle_rate = (ScopedRateThrottle,)
    throttle_scope = 'get_payment'

    @staticmethod
    def extract_error_from_provider_response(payment):
        """
        Identify error based on Payment Provider Response for failed payments.
        """
        payment_state = payment["state"]
        if payment_state == PaymentState.FAILED.value:
            provider_response_body = payment["provider_response_body"]
            payment_error = provider_response_body['data']['object']['last_payment_error']
            if payment_error['code'] == StripeErrorCode.CARD_DECLINED.value:
                return {'errors': [{'error_code': TransactionDeclinedAPIError.default_code}]}
        return None

    @staticmethod
    def set_cache(payment, filter_params):
        """
        Sets payment cache based on payment current state.
        """
        payment_state = payment["state"]
        if payment_state == PaymentState.COMPLETED.value:
            PaymentCache().set_paid_cache_payment(payment)
        elif payment_state == PaymentState.PENDING.value:
            PaymentCache().set_processing_cache_payment(payment)
        elif payment_state == PaymentState.FAILED.value:
            filter_params.pop('payment_number')  # remove payment_number from filter input to get any new payments.
            new_payment = PaymentRequested.run_filter(**filter_params)
            # For failed payment, there should be new_payment_number.
            payment['new_payment_number'] = new_payment['payment_number']
            PaymentCache().set_processing_cache_payment(payment)
        else:
            logger.exception(f"[PaymentGetView] Received an unhandled payment state. payment: {payment}")
            raise UnhandledPaymentStateAPIError

    def get(self, request):
        """Get Payment details including it's status"""
        params = {
            # 'edx_lms_user_id': request.user.lms_user_id,
            'edx_lms_user_id': 1,
            'order_uuid': request.query_params.get('order_uuid'),
            'payment_number': request.query_params.get('payment_number'),
        }
        input_serializer = GetPaymentInputSerializer(data=params)
        input_serializer.is_valid(raise_exception=True)
        filter_params = input_serializer.data

        payment = PaymentCache().get_cache_payment(filter_params['payment_number'])
        if not payment:
            # Cached payment not found. We have to call Titan to fetch Payment information
            payment = PaymentRequested.run_filter(**filter_params)
            self.set_cache(payment, filter_params)

        errors = self.extract_error_from_provider_response(payment)
        if errors:
            payment.update(errors)

        output_serializer = GetPaymentOutputSerializer(data=payment)
        output_serializer.is_valid(raise_exception=True)
        return Response(output_serializer.data)


class DraftPaymentCreateView(APIView):
    """Create Draft Payment View."""
    authentication_classes = (JwtAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        """Gets initial information required to collect payment details on a basket."""
        params = {
            'edx_lms_user_id': request.user.lms_user_id,
        }
        input_serializer = DraftPaymentCreateViewInputSerializer(data=params)
        input_serializer.is_valid(raise_exception=True)
        params = input_serializer.data
        try:
            payment_details = DraftPaymentRequested.run_filter(**params)
            if payment_details and payment_details['capture_context']['state'] == PaymentState.COMPLETED.value:
                payment_details['capture_context'] = {}
        except NoActiveOrder:
            logger.debug('[DraftPaymentCreateView] No active order found for user: %s, '
                         'returning empty caputre_context', request.user.lms_user_id)
            payment_details = {'capture_context': {}}
        return Response(payment_details)


class GetActiveOrderView(APIView):
    """Get Active Order View"""
    authentication_classes = (JwtAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        """return the user's current active order"""
        params = {
            'edx_lms_user_id': request.user.lms_user_id
        }
        input_serializer = GetActiveOrderInputSerializer(data=params)
        input_serializer.is_valid(raise_exception=True)
        params = input_serializer.data
        order_data = ActiveOrderRequested.run_filter(params)
        return Response(order_data)


class PaymentProcessView(APIView):
    """
    Responsible for start processing payment for user.
    """
    authentication_classes = (JwtAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        """
        method for receiving a request to mark a payment as ready for processing by the payment processor.
        """
        input_data = {
            **request.data,
            'edx_lms_user_id': request.user.lms_user_id
        }
        input_serializer = PaymentProcessInputSerializer(data=input_data)
        input_serializer.is_valid(raise_exception=True)
        params = input_serializer.data
        response_data = PaymentProcessingRequested.run_filter(**params)
        return Response(response_data)
