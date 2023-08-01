"""Serializers for ecommerce service"""
from commerce_coordinator.apps.core import serializers
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
    first_name = serializers.CharField(allow_null=False)
    last_name = serializers.CharField(allow_null=False)
    coupon_code = serializers.CharField(allow_null=True)


class OrderFulfillViewInputSerializer(CoordinatorSerializer):
    """
    Serializer for OrderFulfillView input validation.
    """
    course_id = serializers.CharField(allow_null=False)
    course_mode = serializers.CharField(allow_null=False)
    date_placed = serializers.UnixDateTimeField(allow_null=False)
    email_opt_in = serializers.BooleanField(allow_null=False)
    order_number = serializers.CharField(allow_null=False)
    provider_id = serializers.CharField(allow_null=True)
    user = serializers.CharField(allow_null=False)
