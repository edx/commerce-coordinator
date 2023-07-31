"""Serializers for LMS (edx-platform) service"""
from rest_framework import serializers

from commerce_coordinator.apps.core.serializers import CoordinatorSerializer


# Originally stolen verbatim from Ecomm
class OrderCreatedSignalInputSerializer(CoordinatorSerializer):  # pylint: disable=abstract-method
    """
    Serializer for order_created_signal input validation.
    """
    sku = serializers.ListField(
        child=serializers.CharField(), allow_empty=False
    )
    edx_lms_user_id = serializers.IntegerField(allow_null=False)
    email = serializers.EmailField(allow_null=False)
    coupon_code = serializers.CharField(allow_null=True)
