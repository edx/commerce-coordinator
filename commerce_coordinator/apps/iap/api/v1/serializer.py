"""
Serializers for order creation in the IAP API.

Includes serializers to validate and process the creation of orders from carts,
including handling PayPal order details and optional shipping addresses.
"""

from rest_framework import serializers

class CreateOrderSerializer(serializers.Serializer):
    """
    Serializer for validating the input data required to create an order.

    Fields:
        cart_id (str): The ID of the cart to create the order from. Required.
        order_number (str): The unique order number for the new order. Required.
        payment_method (str): The payment method used (e.g., "paypal"). Required.
        shipping_address (dict, optional): Shipping address information if not already set in the cart.
        paypal_order (dict, optional): Details about the PayPal order, including order ID and payment source.
    """

    cart_id = serializers.CharField(required=True, help_text="ID of the cart to create the order from.")
    order_number = serializers.CharField(required=True, help_text="Unique order number to assign to the new order.")
    payment_method = serializers.CharField(required=True, help_text="Payment method used (e.g., 'paypal').")
    shipping_address = serializers.DictField(required=False, help_text="Shipping address details (optional).")
    paypal_order = serializers.DictField(required=False, help_text="PayPal order details (optional).")

    def create(self, validated_data):
        return validated_data

    def update(self, instance, validated_data):
        return instance


class OrderResponseSerializer(serializers.Serializer):
    """
      Serializer for returning order creation response data.

      Fields:
          order_id (str): The unique identifier of the created order.
          order_number (str): The reference number assigned to the order.
          payment_status (str): The status of the payment (e.g., 'APPROVED', 'Pending').
      """
    order_id = serializers.CharField(help_text="Created order ID.")
    order_number = serializers.CharField(help_text="Order number.")
    payment_status = serializers.CharField(help_text="Payment status.")

    def create(self, validated_data):
        return validated_data

    def update(self, instance, validated_data):
        return instance
