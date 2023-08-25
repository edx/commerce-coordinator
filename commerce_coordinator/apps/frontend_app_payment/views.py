"""
Views for the frontend_app_payment app
"""
import logging

from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from commerce_coordinator.apps.core.cache import (
    get_cached_payment,
    set_payment_paid_cache,
    set_payment_processing_cache
)
from commerce_coordinator.apps.core.constants import PaymentState
from commerce_coordinator.apps.frontend_app_payment.exceptions import UnhandledPaymentStateAPIError
from commerce_coordinator.apps.titan.exceptions import NoActiveOrder

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

    def get(self, request):
        """Get Payment details including it's status"""
        params = {
            'edx_lms_user_id': request.user.lms_user_id,
            'order_uuid': request.query_params.get('order_uuid'),
            'payment_number': request.query_params.get('payment_number'),
        }
        input_serializer = GetPaymentInputSerializer(data=params)
        input_serializer.is_valid(raise_exception=True)
        params = input_serializer.data
        payment_number = params['payment_number']
        payment = get_cached_payment(payment_number)

        if not payment:
            # Cached payment not found. We have to call Titan to fetch Payment information
            payment = PaymentRequested.run_filter(**params)

            # Set cache for future use
            payment_state = payment["state"]
            if payment_state == PaymentState.COMPLETED.value:
                set_payment_paid_cache(payment)
            elif payment_state == PaymentState.PENDING.value:
                set_payment_processing_cache(payment)
            elif payment_state == PaymentState.FAILED.value:
                params.pop('payment_number')  # remove payment number to get any new payments.
                new_payment = PaymentRequested.run_filter(**params)
                payment['new_payment_number'] = new_payment['payment_number']
                set_payment_processing_cache(payment)
            else:
                logger.exception(f"[PaymentGetView] Received an unhandled payment state. payment: {payment}")
                raise UnhandledPaymentStateAPIError

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
