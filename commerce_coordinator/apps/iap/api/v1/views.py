import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from commerce_coordinator.apps.commercetools.catalog_info.constants import TwoUKeys
from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient

from commerce_coordinator.apps.iap.api.v1.utils import (
    get_ct_customer,
    get_email_domain,
)
from commerce_coordinator.apps.iap.api.v1.serializer import (
    OrderRequestSerializer,
    OrderResponseSerializer,
)

logger = logging.getLogger(__name__)


class CreateOrderView(APIView):
    """
    API view for preparing a cart in CT and then converting it to an order
    for mobile In-App purchase
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request: Request) -> Response:
        """
        Handles POST request for preparing a cart in CT and then converting it
        to an order for mobile In-App purchase
        """
        try:
            serializer = OrderRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            request_data = serializer.validated_data

            client = CommercetoolsAPIClient()

            customer = get_ct_customer(client, request.user)
            cart = client.get_customer_cart(customer.id)

            if cart:
                client.delete_cart(cart)

            order_number = client.get_new_order_number()
            cart = client.create_cart(
                customer=customer,
                order_number=order_number,
                currency=request_data["currency"],
                country=request_data["country"],
                language=request_data["language"],
            )
            payment = client.create_payment(
                cart=cart,
                payment_method=request_data["payment_method"],
                payment_status=request_data["payment_status"],
                payment_processor=request_data["payment_processor"],
                psp_payment_id=request_data["payment_id"],
                psp_transaction_id=request_data["transaction_id"],
            )
            cart = client.update_cart(
                cart=cart,
                sku=request_data["course_run_key"],
                email_domain=get_email_domain(cart.customer_email),
                payment_id=payment.id,
                address=request_data["address"],
            )
            order = client.create_order_from_cart(cart)
            order = client.update_line_items_transition_state(
                order_id=order.id,
                order_version=order.version,
                line_items=order.line_items,
                from_state_id=order.line_items[0].state[0].state.id,
                new_state_key=TwoUKeys.PENDING_FULFILMENT_STATE,
                use_state_id=True,
            )

            response_serializer = OrderResponseSerializer(
                {
                    "order_id": order.id,
                    "order_number": order.order_number,
                }
            )
            serializer.is_valid(raise_exception=True)

            return Response(
                response_serializer.validated_data,
                status=status.HTTP_201_CREATED,
            )
        except Exception as exception:  # pylint: disable=broad-exception-caught
            lms_user_id = request.user.lms_lms_user_id
            message = (
                f"[CreateOrderView] Error creating order for LMS user: {lms_user_id}"
            )

            logger.exception(
                message + f" with error message: {str(exception)}",
                exc_info=exception,
            )

            return Response(
                {"error": message},
                status=status.HTTP_400_BAD_REQUEST,
            )
