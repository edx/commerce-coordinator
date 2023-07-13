"""
Views for the frontend_app_payment app
"""
import logging

from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

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
        payment_details = PaymentRequested.run_filter(params)
        output_serializer = GetPaymentOutputSerializer(data=payment_details)
        output_serializer.is_valid(raise_exception=True)
        return Response(output_serializer.data)


class DraftPaymentCreateView(APIView):
    """Create Draft Payment View."""
    authentication_classes = (JwtAuthentication,)
    permission_classes = (IsAuthenticated,)

    def put(self, request):
        """Gets initial information required to collect payment details on a basket."""
        params = {
            'edx_lms_user_id': request.user.lms_user_id,
        }
        input_serializer = DraftPaymentCreateViewInputSerializer(data=params)
        input_serializer.is_valid(raise_exception=True)
        params = input_serializer.data
        payment_details = DraftPaymentRequested.run_filter(**params)
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
