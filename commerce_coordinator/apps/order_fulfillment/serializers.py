"""Serializers for LMS (edx-platform) service"""
from rest_framework import serializers

from commerce_coordinator.apps.core.serializers import CoordinatorSerializer


class FulfillOrderWebhookSerializer(CoordinatorSerializer):
    """
    Serializer for Fulfill Order Webhook input validation.
    """
    fulfillment_type = serializers.CharField()
    is_fulfilled = serializers.BooleanField()
    entitlement_uuid = serializers.CharField(required=False, allow_null=True)
    order_id = serializers.CharField()
    order_version = serializers.CharField()
    line_item_id = serializers.CharField()
    item_quantity = serializers.IntegerField()
    line_item_state_id = serializers.CharField()
