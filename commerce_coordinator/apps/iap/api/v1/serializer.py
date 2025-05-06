from rest_framework import serializers

from commerce_coordinator.apps.core.serializers import CoordinatorSerializer


class OrderRequestSerializer(CoordinatorSerializer):
    """Serializer for the request data of an order creation request"""

    course_run_key = serializers.CharField(help_text="Course run key")
    payment_method = serializers.CharField(help_text="Payment method")
    payment_status = serializers.CharField(help_text="Payment status")
    payment_processor = serializers.CharField(help_text="Payment processor")
    payment_id = serializers.CharField(help_text="Payment ID")
    transaction_id = serializers.CharField(help_text="Transaction ID")
    price = serializers.DecimalField(
        max_digits=20, decimal_places=2, help_text="Price of the course"
    )
    currency = serializers.CharField(help_text="Currency code")
    country = serializers.CharField(help_text="Country code")
    language = serializers.CharField(help_text="Language code")


class OrderResponseSerializer(CoordinatorSerializer):
    """Serializer for the response data of an order creation request"""

    order_id = serializers.CharField(help_text="Created order ID.")
    order_number = serializers.CharField(help_text="Order number.")
