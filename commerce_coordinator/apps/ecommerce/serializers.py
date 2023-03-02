"""Serializers for ecommerce service"""
from rest_framework import serializers


class OrderCreatedSignalInputSerializer(serializers.Serializer):  # pylint: disable=abstract-method
    """
    Serializer for order_created_signal input validation.
    """
    coupon_code = serializers.CharField(allow_null=True)
    edx_lms_user_id = serializers.IntegerField(allow_null=False)
    email = serializers.EmailField(allow_null=False)
    product_sku = serializers.ListField(
        child=serializers.CharField(), allow_empty=False
    )
