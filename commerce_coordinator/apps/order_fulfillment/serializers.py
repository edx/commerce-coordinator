"""Serializers for LMS (edx-platform) service"""
from rest_framework import serializers

from commerce_coordinator.apps.core.serializers import CoordinatorSerializer


class FulfilledOrderWebhookSerializer(CoordinatorSerializer):
    """
    Serializer for Fulfill Order Webhook input validation.
    """
    fulfillment_type = serializers.CharField()
    is_fulfilled = serializers.BooleanField()
    entitlement_uuid = serializers.CharField(required=False, allow_null=True)
    order_id = serializers.CharField()
    line_item_id = serializers.CharField()


class OrderRevokeLineRequestSerializer(CoordinatorSerializer):
    """
    Serializer for validating the payload for revoking a course line item.
    """
    edx_lms_username = serializers.CharField(allow_null=False)
    course_run_key = serializers.CharField(allow_null=False)
    course_mode = serializers.CharField(allow_null=False)
    lob = serializers.CharField(allow_null=False)
