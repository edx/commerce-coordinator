"""Serializers for frontend_app_payment service"""
from collections import OrderedDict

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
    number = serializers.CharField(allow_null=False)
    orderUuid = serializers.UUIDField(allow_null=False)
    responseCode = serializers.CharField(allow_null=False)
    state = serializers.CharField(allow_null=False)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        ret = OrderedDict()
        ret['payment_number'] = representation['number']
        ret['order_uuid'] = representation['orderUuid']
        ret['key_id'] = representation['responseCode']
        ret['state'] = representation['state']
        return ret
