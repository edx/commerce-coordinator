"""Serializers for LMS (edx-platform) service"""
from typing import Dict

from rest_framework import serializers

from commerce_coordinator.apps.core.serializers import CoordinatorSerializer


class FulfillOrderWebhookSerializer(CoordinatorSerializer):
    """
    Serializer for Fulfill Order Webhook input validation.
    """
    fulfillment_type = serializers.CharField(required=True)
    entitlement_uuid = serializers.CharField(required=False)
    order_id = serializers.CharField(required=True)
    order_version = serializers.CharField(required=True)
    line_item_id = serializers.CharField(required=True)
    item_quantity = serializers.IntegerField(required=True)
    line_item_state_id = serializers.CharField(required=True)
