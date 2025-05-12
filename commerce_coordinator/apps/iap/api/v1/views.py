import datetime
import logging
import uuid

from commercetools import CommercetoolsError
from commercetools.platform.models import Money

from iso4217 import Currency

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
    get_standalone_price_for_sku,
)
from commerce_coordinator.apps.iap.api.v1.serializer import (
    MobileOrderRequestData,
    MobileOrderRequestSerializer,
)

logger = logging.getLogger(__name__)


class MobileCreateOrderView(APIView):
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
            serializer = MobileOrderRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = MobileOrderRequestData(**serializer.validated_data)  # type: ignore

            fraction_digits = Currency(data.currency_code).exponent or 0
            external_price = Money(
                cent_amount=int(data.price.scaleb(fraction_digits)),
                currency_code=data.currency_code,
            )
            standalone_price = get_standalone_price_for_sku(
                sku=data.course_run_key,
            )

            client = CommercetoolsAPIClient(enable_retries=True)
            customer = get_ct_customer(client, request.user)
            cart = client.get_customer_cart(customer.id)

            if cart:
                client.delete_cart(cart)

            order_number = client.get_new_order_number()
            cart = client.create_cart(
                course_run_key=data.course_run_key,
                customer=customer,
                email_domain=get_email_domain(customer.email),
                external_price=external_price,
                order_number=order_number,
            )
            payment = client.create_payment(
                amount_planned=external_price,
                customer_id=customer.id,
                # TODO: finalize source of these
                payment_method="Dummy Card",
                payment_status="Dummy Success",
                payment_processor=data.payment_processor,
                # TODO: fetch from purchase token
                psp_payment_id="Dummy-" + str(uuid.uuid4()),
                psp_transaction_id="Dummy-" + str(uuid.uuid4()),
                psp_transaction_created_at=datetime.datetime.now(),
                usd_cent_amount=standalone_price.cent_amount,
            )
            cart = client.add_payment_to_cart(
                cart=cart,
                payment_id=payment.id,
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

            return Response(
                data={
                    "order_id": order.id,
                    "order_number": order.order_number,
                },
                status=status.HTTP_201_CREATED,
            )
        except CommercetoolsError as err:
            lms_user_id = request.user.lms_user_id
            message = (
                f"[CreateOrderView] Error creating order for LMS user: {lms_user_id}"
            )

            logger.exception(message, exc_info=err)

            return Response(
                {"error": message},
                status=status.HTTP_400_BAD_REQUEST,
            )
