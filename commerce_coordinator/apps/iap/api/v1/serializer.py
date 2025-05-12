from decimal import Decimal
from typing import NamedTuple

from rest_framework import serializers

from commerce_coordinator.apps.core.serializers import CoordinatorSerializer


class MobileOrderRequestSerializer(CoordinatorSerializer):
    """Serializer for the request data of an order creation request"""

    course_run_key = serializers.CharField(help_text="Course run key")
    currency_code = serializers.CharField(help_text="Currency code")
    price = serializers.DecimalField(
        max_digits=20, decimal_places=5, help_text="Price of the course"
    )
    purchase_token = serializers.CharField(help_text="Purchase token")
    payment_processor = serializers.CharField(help_text="Payment processor")


class MobileOrderRequestData(NamedTuple):
    """NamedTuple for the request data of an order creation request"""

    course_run_key: str
    currency_code: str
    price: Decimal
    payment_processor: str
    purchase_token: str
