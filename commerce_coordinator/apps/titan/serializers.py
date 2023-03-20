"""Serializers for Titan service"""
from rest_framework import serializers


class OrderFulfillViewInputSerializer(serializers.Serializer):  # pylint: disable=abstract-method
    """
    Serializer for OrderFulfillView input validation.
    """
    course_id = serializers.CharField(allow_null=False)
    course_mode = serializers.CharField(allow_null=False)
    date_placed = serializers.DateTimeField(allow_null=False)
    edx_lms_user_id = serializers.IntegerField(allow_null=False)
    email_opt_in = serializers.BooleanField(allow_null=False)
    order_number = serializers.UUIDField(allow_null=False)
    provider_id = serializers.CharField(allow_null=True)
