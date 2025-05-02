"""
Views for creating orders via the IAP API.

This module handles the order creation process from an existing commercetools cart,
associates a payment and returns the final order details.
"""

import logging

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.permissions import IsAuthenticated
from django.http import JsonResponse

from commercetools.platform.models import Customer
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

from commerce_coordinator.apps.commercetools.catalog_info.constants import (
    EdXFieldNames,
)
from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient
from commerce_coordinator.apps.iap.api.v1.utils import is_cart_active, set_shipping_address
from commerce_coordinator.apps.iap.api.v1.serializer import CreateOrderSerializer, OrderResponseSerializer

logger = logging.getLogger(__name__)

PAYPAL_PAYMENT_SERVICE_PROVIDER = "PayPal"


class CreateOrderView(APIView):
    """
    API view for preparing a cart in CT and then converting it to an order
    for mobile In-App purchase
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request: Request) -> JsonResponse:
        """
        Handles POST request for preparing a cart in CT and then converting it
        to an order for mobile In-App purchase
        """
        try:
            client = CommercetoolsAPIClient()

            course_run_keys = self._get_course_run_keys(request)
            customer = self._get_ct_customer(client, request.user)
            cart = client.get_customer_cart(customer.id)

            if cart:
                client.delete_cart(cart)

            order_number = client.get_new_order_number()
            cart = client.create_cart(
                customer=customer,
                order_number=order_number,
                # TODO: get from payload
                locale={"language": "en-US", "country": "US", "currency": "USD"},
            )
            cart = client.add_to_cart(cart=cart, skus=course_run_keys)
            cart = client.set_customer_email_domain_on_cart(
                cart=cart,
                email=customer.email,
            )

            # create order

            serializer = CreateOrderSerializer(data=request.data)
            if not serializer.is_valid():
                logger.warning(f"Order creation failed due to invalid input: {serializer.errors}")
                return JsonResponse({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

            data = serializer.validated_data

            order_number = data["order_number"]
            payment_method = data["payment_method"]
            shipping_address_data = data.get("shipping_address")
            paypal_order = data.get("paypal_order") or {
                "id": "TEST12345",
                "status": "APPROVED",
                "paymentSource": {"type": payment_method or "paypal"}
            }


            try:
                cart = set_shipping_address(cart, shipping_address_data, client)
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
                payment = client.base_client.payments.create(payment_draft)
            except CommercetoolsError as e:
                logger.error(f"[CreateOrderView] Failed to create payment: {str(e)}")
                return Response(
                    {"error": "An internal error occurred while processing the payment."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            try:
                cart = client.base_client.carts.update_by_id(
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
                order = client.base_client.orders.create(order_draft)
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
                    order = client.base_client.orders.update_by_id(order.id, update_action)
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

        except Exception as exception:  # pylint: disable=broad-exception-caught
            message = (
                f"[CreateOrderView] Error creating order for LMS user: "
                f"{request.user.lms_user_id} with error message: {str(exception)}"
            )
            logger.exception(message, exc_info=exception)

            return JsonResponse(
                {"error": message},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def _get_ct_customer(self, client: CommercetoolsAPIClient, user) -> Customer:
        """
        Get an existing customer for the authenticated user or create a new one.

        Args:
            client: CommercetoolsAPIClient instance
            user: The authenticated user from the request

        Returns:
            The customer object
        """
        customer = client.get_customer_by_lms_user_id(user.lms_user_id)
        first_name, last_name = user.first_name, user.last_name

        if not (first_name and last_name) and user.full_name:
            splitted_name = user.full_name.split(" ", 1)
            first_name = splitted_name[0]
            last_name = splitted_name[1] if len(splitted_name) > 1 else ""

        if customer:
            updates = self._get_attributes_to_update(
                user, customer, first_name, last_name
            )
            if updates:
                customer = client.update_customer(
                    customer=customer,
                    updates=updates,
                )
        else:
            customer = client.create_customer(
                email=user.email,
                first_name=first_name,
                last_name=last_name,
                lms_user_id=user.lms_user_id,
                lms_username=user.username,
            )

        return customer

    def _get_attributes_to_update(
        self,
        user,
        customer: Customer,
        first_name: str,
        last_name: str,
    ) -> dict[str, str | None]:
        """
        Get the attributes that need to be updated for the customer.

        Args:
            customer: The existing customer object
            user: The authenticated user from the request

        Returns:
            A dictionary of attributes to update with their new values
        """
        updates = {}

        ct_lms_username = None
        if customer.custom and customer.custom.fields:
            ct_lms_username = customer.custom.fields.get(EdXFieldNames.LMS_USER_NAME)

        if ct_lms_username != user.username:
            updates["lms_username"] = user.username

        if customer.email != user.email:
            updates["email"] = user.email

        if customer.first_name != first_name:
            updates["first_name"] = first_name

        if customer.last_name != last_name:
            updates["last_name"] = last_name

        return updates

    def _get_course_run_keys(self, request: Request) -> list[str]:
        """
        Extracts course run keys from the request data.

        Args:
            request: The HTTP request object

        Returns:
            A list of course run keys
        """
        course_run_keys = request.data.get("course_run_key")

        if not course_run_keys:
            raise Exception("No course_run_key provided.")

        return (
            course_run_keys
            if isinstance(course_run_keys, list)
            else [course_run_keys]
        )
