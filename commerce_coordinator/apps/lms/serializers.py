"""Serializers for LMS (edx-platform) service"""
from rest_framework import serializers


class OrderCreatedSignalInputSerializer(serializers.Serializer):  # pylint: disable=abstract-method
    """
    Serializer for order_created_signal input validation.
    """
    product_sku = serializers.ListField(
        child=serializers.CharField(), allow_empty=False
    )
    edx_lms_user_id = serializers.IntegerField(allow_null=False)
    email = serializers.EmailField(allow_null=False)
    first_name = serializers.CharField(allow_null=False)
    last_name = serializers.CharField(allow_null=False)
    coupon_code = serializers.CharField(allow_null=True)
