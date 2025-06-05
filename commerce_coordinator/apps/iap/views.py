"""
Views for the InAppPurchase app
"""

import datetime
import logging
import uuid

import app_store_notifications_v2_validator as ios_validator
import httplib2
from commercetools import CommercetoolsError
from commercetools.platform.models import Money
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

# isort: off
from commerce_coordinator.apps.commercetools.catalog_info.constants import (
    EDX_ANDROID_IAP_PAYMENT_INTERFACE_NAME,
    EDX_IOS_IAP_PAYMENT_INTERFACE_NAME,
    TwoUKeys,
)
from commerce_coordinator.apps.commercetools.catalog_info.edx_utils import (
    get_edx_lms_user_id,
)
from commerce_coordinator.apps.commercetools.clients import (
    CommercetoolsAPIClient,
    Refund,
)
from commerce_coordinator.apps.core.views import SingleInvocationAPIView
from commerce_coordinator.apps.iap.segment_events import (
    emit_checkout_started_event,
    emit_product_added_event,
    emit_order_completed_event,
    emit_payment_info_entered_event,
)
from commerce_coordinator.apps.iap.utils import (
    convert_localized_price_to_ct_cent_amount,
    get_ct_customer,
    get_email_domain,
    get_standalone_price_for_sku,
)
from commerce_coordinator.apps.iap.serializers import (
    MobileOrderRequestData,
    MobileOrderRequestSerializer,
)
from commerce_coordinator.apps.iap.signals import payment_refunded_signal

# isort: on

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

            client = CommercetoolsAPIClient(enable_retries=True)
            customer = get_ct_customer(client, request.user)
            lms_user_id = get_edx_lms_user_id(customer)
            cart = client.get_customer_cart(customer.id)

            external_price = Money(
                cent_amount=convert_localized_price_to_ct_cent_amount(
                    amount=data.price, currency_code=data.currency_code
                ),
                currency_code=data.currency_code,
            )
            standalone_price = get_standalone_price_for_sku(
                sku=data.course_run_key,
            )

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

            emit_checkout_started_event(
                lms_user_id=lms_user_id,
                cart_id=cart.id,
                standalone_price=standalone_price,
                line_items=cart.line_items,
                discount_codes=cart.discount_codes,
                discount_on_line_items=None,
                discount_on_total_price=cart.discount_on_total_price,
            )

            for item in cart.line_items:
                emit_product_added_event(
                    lms_user_id=lms_user_id,
                    cart_id=cart.id,
                    standalone_price=standalone_price,
                    line_item=item,
                    discount_codes=cart.discount_codes,
                )

            dummy_id = str(uuid.uuid4())
            payment = client.create_payment(
                amount_planned=external_price,
                customer_id=customer.id,
                # TODO: finalize source of these
                payment_method="Dummy Card",
                payment_status="succeeded",
                payment_processor=data.payment_processor,
                # TODO: fetch from purchase token
                psp_payment_id=dummy_id,
                psp_transaction_id=dummy_id,
                psp_transaction_created_at=datetime.datetime.now(),
                usd_cent_amount=standalone_price.cent_amount,
            )

            emit_payment_info_entered_event(
                lms_user_id=lms_user_id,
                cart_id=cart.id,
                standalone_price=standalone_price,
                payment_method=payment.payment_method_info.payment_interface,
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

            emit_order_completed_event(
                lms_user_id=lms_user_id,
                cart_id=order.cart.id,
                order_id=order.id,
                standalone_price=standalone_price,
                line_items=cart.line_items,
                payment_method=payment.payment_method_info.payment_interface,
                discount_codes=order.discount_codes,
                discount_on_line_items=None,
                discount_on_total_price=cart.discount_on_total_price,
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


class IOSRefundView(SingleInvocationAPIView):
    """
    Create refunds for orders refunded by Apple

    A 200 response should be returned as soon as possible as Apple
    will retry the event if no response is received.
    """

    http_method_names = ["post"]  # accept POST request only
    authentication_classes = []
    permission_classes = [AllowAny]
    apple_cert_file_path = "commerce_coordinator/apps/iap/AppleRootCA-G3.cer"

    @csrf_exempt
    def post(self, request):
        """
        IOS refund view to receive refund webhook notifications from Apple
        """
        tag = type(self).__name__
        notification = ios_validator.parse(
            request.body, apple_root_cert_path=self.apple_cert_file_path
        )
        notification_type = notification.get("notificationType", "")
        logger.info(
            "Received notification from apple with notification type: "
            f"{notification_type}"
        )
        if notification_type == "REFUND":
            transaction = notification["data"]["signedTransactionInfo"]
            transaction_id = transaction["originalTransactionId"]
            notification_id = notification.get("notificationUUID", transaction_id)

            if self._is_running(tag, notification_id):  # pragma no cover
                self.meta_should_mark_not_running = False
                return Response(status=status.HTTP_200_OK)
            else:
                self.mark_running(tag, notification_id)

            refund: Refund = {
                "id": transaction_id,
                "created": transaction["revocationDate"],
                "amount": convert_localized_price_to_ct_cent_amount(
                    amount=transaction["price"],
                    currency_code=transaction["currency"],
                    # price received from notification is scaled by 1000
                    # Ref: https://developer.apple.com/documentation/appstoreserverapi/jwstransactiondecodedpayload
                    exponent=3,
                ),
                "currency": transaction["currency"],
                "status": "succeeded",
            }
            payment_refunded_signal.send_robust(
                sender=self.__class__,
                payment_interface=EDX_IOS_IAP_PAYMENT_INTERFACE_NAME,
                refund=refund,
            )
        else:
            logger.info(
                f"Ignoring notification type '{notification_type}' from apple"
                "since we are only expecting refund notifications"
            )

        return Response(status=status.HTTP_200_OK)


class TestRefundView(APIView):
    """
    Test view to create a refund for testing purposes
    """

    def post(self, request):
        """
        Create a test refund
        """
        refund: Refund = {
            "id": request.data["transaction_id"],
            "created": int(datetime.datetime.now().timestamp()) * 1000,
            "amount": request.data["price"],
            "currency": request.data["currency_code"],
            "status": "succeeded",
        }
        payment_refunded_signal.send_robust(
            sender=self.__class__,
            payment_interface=f"{request.data['payment_processor']}_edx",
            refund=refund,
        )
        return Response(
            data={"id": refund["id"]},
            status=status.HTTP_200_OK,
        )


class AndroidRefundView(APIView):
    """
    Create refunds for orders refunded by Google
    """

    http_method_names = ["get"]  # accept GET request only
    permission_classes = (IsAuthenticated, IsAdminUser)
    processor_name = "android_iap"
    timeout = 30

    def get(self, request):
        """
        Get all refunds in last 3 days from voidedpurchases api
        and call refund method on every refund.
        """
        configuration = settings.PAYMENT_PROCESSOR_CONFIG[self.processor_name]

        refunds_time = datetime.datetime.now() - datetime.timedelta(
            days=configuration["refunds_age_in_days"]
        )
        refunds_time_in_ms = round(refunds_time.timestamp() * 1000)
        service = self._get_service(configuration)

        voided_purchases_request = (
            service.purchases()  # pylint: disable=no-member
            .voidedpurchases()
            .list(
                packageName=configuration["google_bundle_id"],
                startTime=refunds_time_in_ms,
            )
        )
        voided_purchases_response = voided_purchases_request.execute()
        voided_purchases = voided_purchases_response.get("voidedPurchases", [])

        for voided_purchase in voided_purchases:
            refund: Refund = {
                "id": voided_purchase["orderId"],
                "created": voided_purchase["voidedTimeMillis"],
                # Google voided purchases api does not provide amount or currency
                # This is filled later from payment object in Commercetools
                "amount": "UNSET",
                "currency": "UNSET",
                "status": "succeeded",
            }
            payment_refunded_signal.send_robust(
                sender=self.__class__,
                payment_interface=EDX_ANDROID_IAP_PAYMENT_INTERFACE_NAME,
                refund=refund,
            )

        return Response()

    def _get_service(self, configuration):
        """Create a service to interact with google api."""
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(
            configuration.get("google_service_account_key_file"),
            configuration.get("google_publisher_api_scope"),
        )
        http = httplib2.Http(timeout=self.timeout)
        http = credentials.authorize(http)

        service = build("androidpublisher", "v3", http=http)
        return service
