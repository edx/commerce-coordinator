"""
Views for the frontend_app_payment app
"""
import logging

from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import ActiveOrderRequested, PaymentProcessingRequested, PaymentRequested
from .serializers import (
    GetActiveOrderInputSerializer,
    PaymentProcessInputSerializer
)

logger = logging.getLogger(__name__)


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
