"""
Views for the InAppPurchase app
"""

import base64
import json
import logging
from typing import NamedTuple

import app_store_notifications_v2_validator as ios_validator
from commercetools import CommercetoolsError
from commercetools.platform.models import Money
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from commerce_coordinator.apps.iap.authentication import GoogleSubscriptionAuthentication

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
    get_payment_info_from_purchase_token,
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
        to an order for mobile In-App purchase.
        """
        cart = None
        client = None

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
            price = standalone_price.cent_amount / 100
            payment_info = get_payment_info_from_purchase_token(
                request.data, cart.id, price
            )

            if payment_info["status_code"] != 200:
                error_msg = payment_info["response"].get("error", "Unknown error")
                logger.error(error_msg)
                client.delete_cart(cart)

                return Response(
                    {"error": error_msg},
                    status=payment_info["status_code"],
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

            payment = client.create_payment(
                amount_planned=external_price,
                customer_id=customer.id,
                payment_method=data.payment_processor.replace("-", " ").strip(),
                payment_status="succeeded",
                payment_processor=data.payment_processor,
                psp_payment_id=payment_info["response"]["transaction_id"],
                psp_transaction_id=payment_info["response"]["transaction_id"],
                psp_transaction_created_at=payment_info["response"]["created_at"],
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

            if cart and client:
                client.delete_cart(cart)

            return Response(
                {"error": message},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class IOSRefundView(SingleInvocationAPIView):
    """
    Create refunds for orders refunded by Apple
    """

    http_method_names = ["post"]
    authentication_classes = []
    permission_classes = [AllowAny]
    apple_cert_file_path = "commerce_coordinator/apps/iap/AppleRootCA-G3.cer"

    @csrf_exempt
    def post(self, request):
        """
        Handles POST requests for refund webhook notifications from Apple.

        Returns a 200 response as soon as possible to prevent Apple
        from retrying the event.
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


class GoogleNotification(NamedTuple):
    """NamedTuple for the Google notification data"""

    version: str
    packageName: str
    eventTimeMillis: str
    oneTimeProductNotification: dict[str, str] | None = None
    subscriptionNotification: dict[str, str] | None = None
    voidedPurchaseNotification: dict[str, str] | None = None
    testNotification: dict[str, str] | None = None

    @property
    def notification_type(self) -> str | None:
        """Gets the type of notification"""
        return next(
            (
                key
                for key, value in self._asdict().items()  # pylint: disable=no-member
                if "Notification" in key and value is not None
            ),
            None,
        )

    @property
    def data(self) -> dict[str, str]:
        """Gets the data from the notification"""
        notification_type = self.notification_type
        return getattr(self, notification_type) if notification_type else {}


class AndroidRefundView(SingleInvocationAPIView):
    """
    Create refunds for orders refunded by Google
    """

    http_method_names = ["post"]
    authentication_classes = [GoogleSubscriptionAuthentication]
    permission_classes = [AllowAny]
    throttle_classes = []
    refund_subscription_type = (
        settings.PAYMENT_PROCESSOR_CONFIG['edx']['android_iap']['iap_android_refund_push_subscription']
    )

    @csrf_exempt
    def post(self, request):
        """
        Handles POST requests for refund webhook notifications from Google.

        Returns a 200 response as soon as possible to prevent Google
        from retrying the event.
        """
        tag = type(self).__name__
        notification_event = request.data
        message = notification_event.get("message", {})
        message_id = message.get("messageId", "")
        subscription_type = notification_event.get("subscription", "unknown")
        ok_response = Response(status=status.HTTP_200_OK)

        logger.info(
            "Received notification from google with subscription type: "
            f"{subscription_type}"
        )

        if self._is_running(tag, message_id):  # pragma no cover
            self.meta_should_mark_not_running = False
            return ok_response
        else:
            self.mark_running(tag, message_id)

        if subscription_type != self.refund_subscription_type:
            logger.info(
                f"Ignoring subscription type '{subscription_type}' from google "
                "since we are only expecting refund notifications"
            )
            return ok_response

        # Decode the base64 encoded data in the message
        # Ref: https://developer.android.com/google/play/billing/rtdn-reference#encoding
        notification = GoogleNotification(
            **json.loads(base64.b64decode(message.get("data", {})).decode("utf-8"))
        )
        notification_type = notification.notification_type

        # Android calls refunded purchases as Voided Purchase
        # and we expect a voidedPurchaseNotification for refund
        # Ref: https://developer.android.com/google/play/billing/rtdn-reference#voided-purchase
        if notification_type != "voidedPurchaseNotification":
            logger.info(
                f"Ignoring notification type '{notification_type}' from google "
                "since we are only expecting refund notifications"
            )
            return ok_response

        voided_purchase = notification.data

        # The refundType for a voided purchase can have the following values:
        # (1) REFUND_TYPE_FULL_REFUND - The purchase has been fully voided.
        # (2) REFUND_TYPE_QUANTITY_BASED_PARTIAL_REFUND - The purchase has been
        # partially voided by a quantity-based partial refund, applicable only
        # to multi-quantity purchases.
        # Ref: https://developer.android.com/google/play/billing/rtdn-reference#voided-purchase
        refund_type = voided_purchase.get("refundType")
        # We expect full refund notifications as we do not have multi-quantity purchase
        if refund_type != 1:
            logger.info(
                f"Ignoring notification from google with refund type '{refund_type}' "
                "since we are only expecting full refund notification"
            )
            return ok_response

        refund: Refund = {
            "id": voided_purchase["orderId"],
            # We use the event time from the notification as the refund creation
            # time in CT. This may not be the actual refund time, since the event
            # is received some time after Google processes the refund. However,
            # as we don't have a concrete use case for the exact refund timestamp,
            # this approximation is acceptable.
            "created": notification.eventTimeMillis,
            # Google refund notification does not provide amount or currency
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

        return ok_response
