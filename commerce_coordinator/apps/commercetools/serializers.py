"""Serializers for CommerceTools service"""

from commerce_coordinator.apps.core import serializers
from commerce_coordinator.apps.core.serializers import CoordinatorSerializer


class OrderMessageDetailSerializer(CoordinatorSerializer):
    """
    Serializer for CommerceTools message 'detail'
    """
    orderId = serializers.CharField(allow_null=False)
    orderState = serializers.CharField(allow_null=False)
    oldOrderState = serializers.CharField()

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['order_id'] = representation.pop('orderId')
        representation['order_state'] = representation.pop('orderState')
        representation['old_order_state'] = representation.pop('oldOrderState')
        return representation


class OrderMessageInputSerializer(CoordinatorSerializer):
    """
    Serializer for commercetools message input
    """
    detail = OrderMessageDetailSerializer(allow_null=False)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation = representation.pop('detail')
        return representation


class OrderFulfillViewInputSerializer(CoordinatorSerializer):
    """
    Serializer for OrderFulfillView input validation.
    """
    course_id = serializers.CharField(allow_null=False)
    course_mode = serializers.CharField(allow_null=False)
    date_placed = serializers.CharField(allow_null=False)
    email_opt_in = serializers.BooleanField(allow_null=False)
    order_number = serializers.CharField(allow_null=False)
    provider_id = serializers.CharField(allow_null=True)
    source_system = serializers.CharField(allow_null=False)
    edx_lms_user_id = serializers.IntegerField(allow_null=False)


class OrderReturnedViewMessageDetailSerializer(CoordinatorSerializer):
    """
    Serializer for OrderReturnedView message detail.
    """
    resource = serializers.DictField(child=serializers.CharField())

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        order_id = representation['resource'].get('id')
        if order_id:
            representation['order_id'] = order_id
        representation.pop('resource')
        return representation


class OrderReturnedViewMessageInputSerializer(CoordinatorSerializer):
    """
    Serializer for OrderReturnedView message input
    """
    detail = OrderReturnedViewMessageDetailSerializer(allow_null=False)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation = representation.pop('detail')
        return representation
