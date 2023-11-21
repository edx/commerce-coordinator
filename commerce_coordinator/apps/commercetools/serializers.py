"""Serializers for CommerceTools service"""

from commerce_coordinator.apps.core import serializers
from commerce_coordinator.apps.core.serializers import CoordinatorSerializer


class OrderFulfillMessageDetailSerializer(CoordinatorSerializer):
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


class OrderFulfillMessageInputSerializer(CoordinatorSerializer):
    """
    Serializer for commercetools message input
    """
    detail = OrderFulfillMessageDetailSerializer(allow_null=False)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation = representation.pop('detail')
        return representation
