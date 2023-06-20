"""Serializers for Titan service"""
from collections import OrderedDict

from commerce_coordinator.apps.core import serializers


class OrderFulfillViewInputSerializer(serializers.Serializer):  # pylint: disable=abstract-method
    """
    Serializer for OrderFulfillView input validation.
    """
    course_id = serializers.CharField(allow_null=False)
    course_mode = serializers.CharField(allow_null=False)
    date_placed = serializers.UnixDateTimeField(allow_null=False)
    edx_lms_user_id = serializers.IntegerField(allow_null=False)
    email_opt_in = serializers.BooleanField(allow_null=False)
    order_number = serializers.UUIDField(allow_null=False)
    provider_id = serializers.CharField(allow_null=True)


class PaymentSerializer(serializers.Serializer):  # pylint: disable=abstract-method
    """
    Serializer for Titan Payment object.

    We feed this serializer with Titan's API Payment dict, and it is responsible transform it into a new dict
    that we use in coordinator system. We can rename key names here.
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
