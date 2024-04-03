"""Serializers for LMS (edx-platform) service"""
from rest_framework import serializers

from commerce_coordinator.apps.core.serializers import CoordinatorSerializer


class OrderCreatedSignalInputSerializer(CoordinatorSerializer):
    """
    Serializer for order_created_signal input validation.
    """
    sku = serializers.ListField(
        child=serializers.CharField(), allow_empty=False
    )
    edx_lms_user_id = serializers.IntegerField(allow_null=False)
    email = serializers.EmailField(allow_null=False)
    coupon_code = serializers.CharField(allow_null=True)


class EnrollmentAttributeSerializer(CoordinatorSerializer):
    """
    Serializer for the ``enrollment_attributes`` key.
    """
    namespace = serializers.CharField(allow_null=False)
    name = serializers.CharField(allow_null=False)
    value = serializers.CharField(allow_null=False)


class RefundViewInputSerializer(CoordinatorSerializer):
    """
    Serializer for RefundView input validation.
    """
    course_id = serializers.CharField(allow_null=True)
    enrollment_attributes = serializers.ListField(
        child=EnrollmentAttributeSerializer(allow_null=True)
    )
    username = serializers.CharField(allow_null=True)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        for attribute in representation['enrollment_attributes']:
            if attribute['namespace'] == 'order':
                if attribute['name'] == 'order_id':
                    representation['order_id'] = attribute['value']
                if attribute['name'] == 'order_line_item_id':
                    representation['order_line_item_id'] = attribute['value']
        return representation


class OrderRefundRequestedFilterInputSerializer(CoordinatorSerializer):
    """
    Serializer for OrderRefundRequested input validation.
    """
    order_id = serializers.UUIDField(allow_null=False)
    order_line_item_id = serializers.UUIDField(allow_null=False)
