"""Serializers for frontend_app_payment service"""
from rest_framework.exceptions import ValidationError

from commerce_coordinator.apps.core import serializers
from commerce_coordinator.apps.core.serializers import CoordinatorSerializer


class GetPaymentInputSerializer(CoordinatorSerializer):
    """
    Serializer for PaymentGetView input validation.
    """
    payment_number = serializers.CharField(allow_null=False)
    order_uuid = serializers.UUIDField(allow_null=False)
    edx_lms_user_id = serializers.IntegerField(allow_null=False)


class GetPaymentOutputSerializer(CoordinatorSerializer):
    """
    Serializer for PaymentGetView output validation.
    """
    state = serializers.CharField(allow_null=False)
    new_payment_number = serializers.CharField(required=False)
    errors = serializers.JSONField(required=False)


class DraftPaymentCreateViewInputSerializer(CoordinatorSerializer):
    """
    Serializer for DraftPaymentCreateView input validation.
    """
    edx_lms_user_id = serializers.IntegerField(allow_null=False)


class DraftPaymentCreateViewOutputSerializer(CoordinatorSerializer):
    """
    Serializer for DraftPaymentCreateView input validation.
    """
    class CaptureContextInnerSerializer(CoordinatorSerializer):
        """
        Serializer for DraftPaymentCreateView's inner dictionary
        """
        order_id = serializers.UUIDField(allow_null=False)
        key_id = serializers.CharField(allow_null=False)

        # Currently these are returned but unused by f-a-Payment. (THES-235)

        payment_number = serializers.CharField(allow_null=False)
        state = serializers.CharField(allow_null=False)

    capture_context = CaptureContextInnerSerializer()


class GetActiveOrderInputSerializer(CoordinatorSerializer):
    """
    Serializer for GetActiveOrderView input validation
    """
    edx_lms_user_id = serializers.IntegerField(allow_null=False)


class PaymentProcessInputSerializer(CoordinatorSerializer):

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
