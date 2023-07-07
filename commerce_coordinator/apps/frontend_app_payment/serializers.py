"""Serializers for frontend_app_payment service"""
from rest_framework.exceptions import ValidationError

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


class DraftPaymentCreateViewInputSerializer(serializers.Serializer):  # pylint: disable=abstract-method
    """
    Serializer for DraftPaymentCreateView input validation.
    """
    edx_lms_user_id = serializers.IntegerField(allow_null=False)


class DraftPaymentCreateViewOutputSerializer(serializers.Serializer):  # pylint: disable=abstract-method
    """
    Serializer for DraftPaymentCreateView input validation.
    """
    payment_number = serializers.CharField(allow_null=False)
    order_uuid = serializers.UUIDField(allow_null=False)
    key_id = serializers.CharField(allow_null=False)
    state = serializers.CharField(allow_null=False)


class GetActiveOrderInputSerializer(serializers.Serializer):  # pylint: disable=abstract-method
    """
    Serializer for GetActiveOrderView input validation
    """
    edx_lms_user_id = serializers.IntegerField(allow_null=False)


class PaymentProcessInputSerializer(serializers.Serializer):  # pylint: disable=abstract-method

    """
    Serializer for PaymentProcessView input validation
    """
    payment_number = serializers.CharField(allow_null=False)
    order_uuid = serializers.UUIDField(allow_null=False)
    payment_intent_id = serializers.CharField(allow_null=False)
    edx_lms_user_id = serializers.IntegerField(allow_null=False)
    skus = serializers.SerializerMethodField()

    def get_skus(self, __):
        skus = self.initial_data.get('skus')
        if skus and isinstance(skus, str):
            return skus.split(',')
        raise ValidationError({'skus': 'Comma seperated `skus` required.'})
