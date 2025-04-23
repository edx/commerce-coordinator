"""
Views for creating orders via the IAP API.

This module handles the order creation process from an existing commercetools cart,
associates a payment and returns the final order details.
"""

import logging

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import JsonResponse

from commercetools.platform.models.order import (
    OrderFromCartDraft,
    OrderUpdate,
    OrderTransitionLineItemStateAction,
)
from commercetools.platform.models.payment import (
    PaymentDraft,
    PaymentMethodInfo,
    PaymentStatusDraft,
)
from commercetools.platform.models.cart import (
    CartAddPaymentAction,
)
from commercetools.platform.models.common import Reference, ReferenceTypeId
from commercetools.platform.models.state import StateResourceIdentifier
from commercetools.exceptions import CommercetoolsError

from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient
from commerce_coordinator.apps.iap.api.v1.utils import is_cart_active, set_shipping_address
from commerce_coordinator.apps.iap.api.v1.serializer import CreateOrderSerializer, OrderResponseSerializer

logger = logging.getLogger(__name__)

PAYPAL_PAYMENT_SERVICE_PROVIDER = "PayPal"

class CreateOrderView(APIView):
    """
    API view for creating an order from a commercetools cart and payment.
    Handles validation, optional shipping, PayPal payment creation,
    payment attachment, and order creation with state transitions.
    """
    permission_classes = (IsAuthenticated,)

    # pylint: disable=too-many-statements
    def post(self, request):
        """Handles POST request to create an order from a cart and payment."""
        serializer = CreateOrderSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"Order creation failed due to invalid input: {serializer.errors}")
            return JsonResponse({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        cart_id = data["cart_id"]
        order_number = data["order_number"]
        payment_method = data["payment_method"]
        shipping_address_data = data.get("shipping_address")
        paypal_order = data.get("paypal_order") or {
            "id": "TEST12345",
            "status": "APPROVED",
            "paymentSource": {"type": payment_method or "paypal"}
        }

        try:
            ct_client = CommercetoolsAPIClient()

            cart = ct_client.base_client.carts.get_by_id(cart_id)

            if not cart.customer_id or str(cart.customer_id) != str(request.user.customer_id):
                logger.warning(
                    f"[CreateOrderView] Unauthorized cart access attempt by user "
                    f"[{request.user.id}] on cart [{cart.id}]."
                )
                return JsonResponse({'error': 'Unauthorized access to cart.'}, status=status.HTTP_403_FORBIDDEN)

            if not is_cart_active(cart):
                logger.error(f"[CreateOrderView] Cart {cart_id} is not active. Current state: {cart.cart_state}")
                return Response(
                    {"error": f"Cart {cart_id} is not in active state. Current state: {cart.cart_state}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                cart = set_shipping_address(cart, shipping_address_data, ct_client)
            except ValueError as e:
                logger.error(f"[CreateOrderView] ValueError encountered: {str(e)}")
                return Response({"error": "Invalid shipping address"}, status=status.HTTP_400_BAD_REQUEST)
            except CommercetoolsError as e:
                logger.error(f"[CreateOrderView] Error setting shipping address: {str(e)}")
                return Response({"error": "Failed to process shipping address."},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            payment_source = paypal_order.get("paymentSource")
            method_key = payment_source.get("type") if payment_source else payment_method
            amount_planned = cart.total_price
            payment_method_info = PaymentMethodInfo(
                payment_interface=PAYPAL_PAYMENT_SERVICE_PROVIDER,
                method=method_key,
                name={"en": method_key},
            )
            payment_status = PaymentStatusDraft(interface_code=paypal_order.get("status"))
            payment_draft = PaymentDraft(
                key=paypal_order.get("id"),
                amount_planned=amount_planned,
                payment_method_info=payment_method_info,
                payment_status=payment_status,
            )

            try:
                payment = ct_client.base_client.payments.create(payment_draft)
            except CommercetoolsError as e:
                logger.error(f"[CreateOrderView] Failed to create payment: {str(e)}")
                return Response(
                    {"error": "An internal error occurred while processing the payment."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            try:
                cart = ct_client.base_client.carts.update_by_id(
                    cart.id,
                    cart.version,
                    [
                        CartAddPaymentAction(
                            payment=Reference(type_id=ReferenceTypeId.PAYMENT, id=payment.id)
                        )
                    ]
                )
            except CommercetoolsError as e:
                logger.error(f"[CreateOrderView] Failed to add payment to cart: {str(e)}")
                return Response({"error": "An internal error occurred while adding payment to the cart."},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            try:
                order_draft = OrderFromCartDraft(
                    id=cart.id,
                    version=cart.version,
                    order_number=order_number,
                )
                order = ct_client.base_client.orders.create(order_draft)
                logger.info(f"[CreateOrderView] Order created: {order.id}")
            except CommercetoolsError as e:
                logger.error(f"[CreateOrderView] Error creating order: {str(e)}")
                return Response({"error": "Failed to create order."},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            try:
                transition_actions = [
                    OrderTransitionLineItemStateAction(
                        line_item_id=item.id,
                        quantity=item.quantity,
                        from_state=StateResourceIdentifier(id=item.state[0].state.id),
                        to_state=StateResourceIdentifier(key="2u-fulfillment-pending-state"),
                    )
                    for item in order.line_items if item.state
                ]

                if transition_actions:
                    update_action = OrderUpdate(version=order.version, actions=transition_actions)
                    order = ct_client.base_client.orders.update_by_id(order.id, update_action)
                    logger.info(f"[CreateOrderView] Line item states transitioned for order {order.id}")
            except CommercetoolsError as e:
                logger.error(f"[CreateOrderView] Error transitioning line item state for order {order.id}: {str(e)}")

            logger.info(f"[CreateOrderView] Successfully created order [{order.id}] for cart [{cart.id}].")

            response_data = {
                'order_id': order.id,
                'order_number': order.order_number,
                'payment_status': (
                    payment.payment_status.state.value
                    if payment.payment_status and payment.payment_status.state else
                    payment.payment_status.interface_code
                    if payment.payment_status and payment.payment_status.interface_code else
                    'Pending'
                ),
            }

            response_serializer = OrderResponseSerializer(response_data)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e: # pylint: disable=broad-exception-caught
            logger.exception("[CreateOrderView] Unexpected error")
            return Response({"error": "An internal server error occurred."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
