"""Serializers for frontend_app_payment service"""
from commerce_coordinator.apps.core import serializers


class GetPaymentInputSerializer(serializers.Serializer):  # pylint: disable=abstract-method
    """
    Serializer for OrderFulfillView input validation.
    """
    payment_number = serializers.CharField(allow_null=False)
    order_uuid = serializers.UUIDField(allow_null=False)
    edx_lms_user_id = serializers.IntegerField(allow_null=False)


class GetPaymentOutputSerializer(serializers.Serializer):  # pylint: disable=abstract-method
    """
    Serializer for OrderFulfillView input validation.
    """
    state = serializers.CharField(allow_null=False)


class GetActiveOrderInputSerializer(serializers.Serializer):  # pylint: disable=abstract-method
    """
    Serializer for GetActiveOrderView input validation
    """
    edx_lms_user_id = serializers.IntegerField(allow_null=False)
