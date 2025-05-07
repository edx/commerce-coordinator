from decimal import Decimal
from typing import TypedDict

from rest_framework import serializers

from commerce_coordinator.apps.core.serializers import CoordinatorSerializer


class OrderRequestSerializer(CoordinatorSerializer):
    """Serializer for the request data of an order creation request"""

    course_run_key = serializers.CharField(help_text="Course run key")
    purchase_token = serializers.CharField(help_text="Payment processor")
    payment_processor = serializers.CharField(help_text="Payment processor")
    price = serializers.DecimalField(
        max_digits=20, decimal_places=2, help_text="Price of the course"
    )
    currency = serializers.CharField(help_text="Currency code")


class OrderResponseSerializer(CoordinatorSerializer):
    """Serializer for the response data of an order creation request"""

    order_id = serializers.CharField(help_text="Created order ID.")
    order_number = serializers.CharField(help_text="Order number.")


class OrderRequestData(TypedDict):
    """TypedDict for the request data of an order creation request"""
    course_run_key: str
    purchase_token: str
    payment_processor: str
    price: Decimal
    currency: str
