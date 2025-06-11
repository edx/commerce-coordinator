"""
Tests for the InAppPurchase app views.
"""

import base64
import json
from unittest import mock

import ddt
from commercetools.exceptions import CommercetoolsError
from commercetools.platform.models import Money
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


@ddt.ddt
@mock.patch("commerce_coordinator.apps.iap.views.CommercetoolsAPIClient")
class MobileCreateOrderViewTests(APITestCase):
    """
    Tests for mobile order creation view.
    """

    test_user_username = "test"
    test_user_email = "test@example.com"
    test_user_password = "secret"
    url = reverse("iap:create_order")

    valid_payload = {
        "course_run_key": "course-v1:edX+DemoX+Demo_Course",
        "price": "49.99",
        "currency_code": "JPY",
        "purchase_token": "test-purchase-token",
        "payment_processor": "apple-iap",
    }

    invalid_payload = {
        "course_run_key": "",
        "price": "",
        "currency_code": "",
        "payment_processor": "",
    }

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            self.test_user_username,
            self.test_user_email,
            self.test_user_password,
        )

    def tearDown(self):
        mock.patch.stopall()
        super().tearDown()
        self.client.logout()

    def authenticate_user(self):
        """Helper to authenticate test user."""
        self.client.login(
            username=self.test_user_username, password=self.test_user_password
        )
        self.client.force_authenticate(user=self.user)

    def test_view_rejects_unauthorized(self, _):
        self.client.logout()
        response = self.client.post(self.url, self.valid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @mock.patch("commerce_coordinator.apps.iap.views.get_ct_customer")
    @mock.patch("commerce_coordinator.apps.iap.views.get_standalone_price_for_sku")
    @mock.patch("commerce_coordinator.apps.iap.views.get_email_domain")
    @mock.patch("commerce_coordinator.apps.iap.views.get_edx_lms_user_id")
    def test_post_with_invalid_data_fails(self, *_):
        self.authenticate_user()
        response = self.client.post(self.url, self.invalid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch("commerce_coordinator.apps.iap.views.emit_order_completed_event")
    @mock.patch(
        "commerce_coordinator.apps.iap.views.emit_payment_info_entered_event"
    )
    @mock.patch("commerce_coordinator.apps.iap.views.emit_product_added_event")
    @mock.patch("commerce_coordinator.apps.iap.views.emit_checkout_started_event")
    @mock.patch("commerce_coordinator.apps.iap.views.get_ct_customer")
    @mock.patch("commerce_coordinator.apps.iap.views.get_standalone_price_for_sku")
    @mock.patch("commerce_coordinator.apps.iap.views.get_email_domain")
    @mock.patch("commerce_coordinator.apps.iap.views.get_edx_lms_user_id")
    @mock.patch("commerce_coordinator.apps.iap.utils.IAPPaymentProcessor")
    @mock.patch("uuid.uuid4")
    def test_successful_order_creation(
        self,
        mock_uuid,
        mock_payment_processor,
        mock_get_edx_lms_user_id,
        mock_get_email_domain,
        mock_get_standalone_price,
        mock_get_ct_customer,
        *args,
    ):
        mock_ct_client = args[-1]
        self.authenticate_user()
        mock_uuid.return_value = "test-uuid"

        self.valid_payload = {
            "payment_processor": "ios-iap",  # Must be valid!
            "course_run_key": "demo-course-run",
            "price": "49.99",
            "currency_code": "USD",
            "purchase_token": "dummy-token"
        }

        # Mock the validate_iap return value
        mock_instance = mock_payment_processor.return_value
        mock_instance.validate_iap.return_value = {
            "receipt": {"receipt_creation_date": "2025-05-21T12:00:00Z"},
            "transaction_id": "txn-123",
            "in_app": [{"product_id": "demo-course-run", "original_transaction_id": "txn-123"}]
        }

        mock_customer = mock.MagicMock()
        mock_customer.id = "customer-123"
        mock_customer.email = self.test_user_email
        mock_get_ct_customer.return_value = mock_customer

        mock_get_email_domain.return_value = "example.com"
        mock_get_standalone_price.return_value = Money(
            cent_amount=4999, currency_code="USD"
        )
        mock_get_edx_lms_user_id.return_value = 12345

        mock_cart = mock.MagicMock()
        mock_cart.id = "cart-123"
        mock_ct_client.return_value.get_customer_cart.return_value = None
        mock_ct_client.return_value.create_cart.return_value = mock_cart

        mock_payment = mock.MagicMock()
        mock_payment.id = "payment-123"
        mock_ct_client.return_value.create_payment.return_value = mock_payment

        mock_order = mock.MagicMock()
        mock_order.id = "order-123"
        mock_order.order_number = "ORDER-123"
        mock_order.version = 1
        mock_line_item = mock.MagicMock()
        mock_line_item.state = [mock.MagicMock(state=mock.MagicMock(id="state-123"))]
        mock_order.line_items = [mock_line_item]
        mock_ct_client.return_value.create_order_from_cart.return_value = mock_order
        mock_ct_client.return_value.update_line_items_transition_state.return_value = (
            mock_order
        )

        response = self.client.post(self.url, self.valid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data, {"order_id": "order-123", "order_number": "ORDER-123"}
        )

    def test_commercetools_error_handling(self, mock_ct_client):
        """Test handling of CommercetoolsError."""
        self.authenticate_user()
        mock_ct_client.return_value.get_customer_cart.side_effect = (
            CommercetoolsError(message="Error creating cart", errors=[], response={})
        )

        response = self.client.post(self.url, self.valid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("error", response.data)

    @ddt.data(
        {"price": "invalid", "currency_code": "USD"},
        {"price": "49.99", "payment_processor": ""},
        {"course_run_key": "", "price": "49.99"},
    )
    @mock.patch("commerce_coordinator.apps.iap.views.get_ct_customer")
    @mock.patch("commerce_coordinator.apps.iap.views.get_standalone_price_for_sku")
    @mock.patch("commerce_coordinator.apps.iap.views.get_email_domain")
    @mock.patch("commerce_coordinator.apps.iap.views.get_edx_lms_user_id")
    def test_invalid_request_variations(self, invalid_data, *_):
        """Test various invalid request scenarios."""
        self.authenticate_user()
        payload = self.valid_payload.copy()
        payload.update(invalid_data)

        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch("commerce_coordinator.apps.iap.views.emit_order_completed_event")
    @mock.patch("commerce_coordinator.apps.iap.views.emit_payment_info_entered_event")
    @mock.patch("commerce_coordinator.apps.iap.views.emit_product_added_event")
    @mock.patch("commerce_coordinator.apps.iap.views.emit_checkout_started_event")
    @mock.patch("commerce_coordinator.apps.iap.views.get_ct_customer")
    @mock.patch("commerce_coordinator.apps.iap.views.get_standalone_price_for_sku")
    @mock.patch("commerce_coordinator.apps.iap.views.get_email_domain")
    @mock.patch("commerce_coordinator.apps.iap.views.get_edx_lms_user_id")
    @mock.patch("commerce_coordinator.apps.iap.utils.IAPPaymentProcessor")
    @mock.patch("uuid.uuid4")
    def test_existing_cart_is_deleted(
        self,
        mock_uuid,
        mock_payment_processor,
        mock_get_edx_lms_user_id,
        mock_get_email_domain,
        mock_get_standalone_price,
        mock_get_ct_customer,
        _mock_emit_checkout_started_event,
        _mock_emit_product_added_event,
        _mock_emit_payment_info_entered_event,
        _mock_emit_order_completed_event,
        mock_ct_client,
    ):

        self.authenticate_user()
        mock_uuid.return_value = "test-uuid"

        self.valid_payload = {
            "payment_processor": "ios-iap",
            "course_run_key": "demo-course-run",
            "price": "49.99",
            "currency_code": "USD",
            "purchase_token": "dummy-token"
        }

        mock_instance = mock_payment_processor.return_value
        mock_instance.validate_iap.return_value = {
            "receipt": {"receipt_creation_date": "2025-05-21T12:00:00Z"},
            "transaction_id": "txn-123",
            "in_app": [{"product_id": "demo-course-run", "original_transaction_id": "txn-123"}]
        }

        mock_customer = mock.MagicMock()
        mock_customer.id = "customer-123"
        mock_customer.email = self.test_user_email
        mock_get_ct_customer.return_value = mock_customer

        mock_get_email_domain.return_value = "example.com"
        mock_get_standalone_price.return_value = mock.MagicMock(
            cent_amount=4999,
            currency_code="USD",
            fraction_digits=2,
        )
        mock_get_edx_lms_user_id.return_value = 12345

        existing_cart = mock.MagicMock()
        existing_cart.id = "old-cart-id"
        mock_ct_client.return_value.get_customer_cart.return_value = existing_cart
        mock_ct_client.return_value.create_cart.return_value = mock.MagicMock(id="new-cart-id")
        mock_ct_client.return_value.create_payment.return_value = mock.MagicMock(id="payment-id")

        mock_order = mock.MagicMock()
        mock_order.id = "order-123"
        mock_order.order_number = "ORDER-123"
        mock_order.version = 1
        mock_order.cart.id = "new-cart-id"
        mock_line_item = mock.MagicMock()
        mock_line_item.state = [mock.MagicMock(state=mock.MagicMock(id="state-id"))]
        mock_order.line_items = [mock_line_item]
        mock_ct_client.return_value.create_order_from_cart.return_value = mock_order
        mock_ct_client.return_value.update_line_items_transition_state.return_value = mock_order

        response = self.client.post(self.url, self.valid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_ct_client.return_value.delete_cart.assert_any_call(existing_cart)

    @mock.patch("commerce_coordinator.apps.iap.views.get_ct_customer")
    @mock.patch("commerce_coordinator.apps.iap.views.get_standalone_price_for_sku")
    @mock.patch("commerce_coordinator.apps.iap.views.get_email_domain")
    @mock.patch("commerce_coordinator.apps.iap.views.get_edx_lms_user_id")
    @mock.patch("commerce_coordinator.apps.iap.views.get_payment_info_from_purchase_token")
    def test_payment_processor_returns_error_and_cart_is_deleted(
        self,
        mock_get_payment_info,
        mock_get_edx_lms_user_id,
        mock_get_email_domain,
        mock_get_standalone_price,
        mock_get_ct_customer,
        mock_ct_client,
    ):
        """Test handling when payment processor returns an error (non-200 status)."""
        self.authenticate_user()

        mock_customer = mock.MagicMock(id="customer-123", email=self.test_user_email)
        mock_get_ct_customer.return_value = mock_customer
        mock_cart = mock.MagicMock(id="cart-123")
        mock_ct_client.return_value.get_customer_cart.return_value = None
        mock_ct_client.return_value.create_cart.return_value = mock_cart
        mock_get_email_domain.return_value = "example.com"
        mock_get_standalone_price.return_value = Money(cent_amount=4999, currency_code="USD")
        mock_get_edx_lms_user_id.return_value = 12345

        mock_get_payment_info.return_value = {
            "status_code": 400,
            "response": {"error": "Invalid receipt"},
        }

        response = self.client.post(self.url, self.valid_payload, format="json")
        mock_ct_client.return_value.delete_cart.assert_called_once_with(mock_cart)
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)
        self.assertEqual(response.data["error"], "Invalid receipt")

        @mock.patch("commerce_coordinator.apps.iap.views.get_ct_customer")
        @mock.patch("commerce_coordinator.apps.iap.views.get_standalone_price_for_sku")
        @mock.patch("commerce_coordinator.apps.iap.views.get_email_domain")
        @mock.patch("commerce_coordinator.apps.iap.views.get_edx_lms_user_id")
        @mock.patch("commerce_coordinator.apps.iap.views.get_payment_info_from_purchase_token")
        def test_payment_processor_returns_error_and_cart_is_deleted(
            self,
            mock_get_payment_info,
            mock_get_edx_lms_user_id,
            mock_get_email_domain,
            mock_get_standalone_price,
            mock_get_ct_customer,
            mock_ct_client,
        ):
            """Test handling when payment processor returns an error (non-200 status)."""
            self.authenticate_user()

            mock_customer = mock.MagicMock(id="customer-123", email=self.test_user_email)
            mock_get_ct_customer.return_value = mock_customer
            mock_cart = mock.MagicMock(id="cart-123")
            mock_ct_client.return_value.get_customer_cart.return_value = None
            mock_ct_client.return_value.create_cart.return_value = mock_cart
            mock_get_email_domain.return_value = "example.com"
            mock_get_standalone_price.return_value = Money(cent_amount=4999, currency_code="USD")
            mock_get_edx_lms_user_id.return_value = 12345

            mock_get_payment_info.return_value = {
                "status_code": 400,
                "response": {"error": "Invalid receipt"},
            }

            response = self.client.post(self.url, self.valid_payload, format="json")
            mock_ct_client.return_value.delete_cart.assert_called_once_with(mock_cart)
            self.assertEqual(response.status_code, 400)
            self.assertIn("error", response.data)
            self.assertEqual(response.data["error"], "Invalid receipt")


class IOSRefundViewTests(APITestCase):
    """
    Tests for iOS refund webhook view.
    """

    url = reverse("iap:ios_refund")

    @mock.patch("commerce_coordinator.apps.iap.views.payment_refunded_signal")
    @mock.patch("commerce_coordinator.apps.iap.views.ios_validator.parse")
    def test_refund_notification_processing(
        self, mock_parse, mock_payment_refunded_signal
    ):
        mock_parse.return_value = {
            "notificationType": "REFUND",
            "notificationUUID": "f5d1e3f0-a6e5-4940-be5d-d6c76d4e4262",
            "data": {
                "signedTransactionInfo": {
                    "transactionId": "730001863682783",
                    "originalTransactionId": "730001863682783",
                    "revocationReason": 0,
                    "revocationDate": 1746057600000,
                    "price": 1010,
                    "currency": "USD",
                }
            },
        }

        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify signal was sent with correct parameters
        mock_payment_refunded_signal.send_robust.assert_called_once()
        args = mock_payment_refunded_signal.send_robust.call_args
        self.assertEqual(args[1]["payment_interface"], "ios_iap_edx")
        refund = args[1]["refund"]
        self.assertEqual(refund["id"], "730001863682783")
        self.assertEqual(refund["created"], 1746057600000)
        self.assertEqual(refund["amount"], 101)
        self.assertEqual(refund["currency"], "USD")
        self.assertEqual(refund["status"], "succeeded")

    @mock.patch("commerce_coordinator.apps.iap.views.payment_refunded_signal")
    @mock.patch("commerce_coordinator.apps.iap.views.ios_validator.parse")
    def test_non_refund_notification(self, mock_parse, mock_payment_refunded_signal):
        """Test handling of non-refund notifications."""
        mock_parse.return_value = {
            "notificationType": "DID_CHANGE_RENEWAL_STATUS",
            "notificationUUID": "f5d1e3f0-a6e5-4940-be5d-d6c76d4e4262",
            "data": {},
        }

        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify signal was not sent
        mock_payment_refunded_signal.send_robust.assert_not_called()


class AndroidRefundViewTests(APITestCase):
    """
    Tests for Android refund view.
    """

    url = reverse("iap:android_refund")
    base_notification_data = {
        "version": "1.0",
        "packageName": "org.edx.mobile",
        "eventTimeMillis": "1746057600000",
    }

    @mock.patch("commerce_coordinator.apps.iap.views.payment_refunded_signal")
    def test_refund_notification_processing(self, mock_payment_refunded_signal):
        """Test processing of refund notifications."""
        notification_data = {
            **self.base_notification_data,
            "voidedPurchaseNotification": {
                "orderId": "GPA.3388-4288-9788-12345",
                "refundType": 1,
            },
        }
        encoded_data = base64.b64encode(
            json.dumps(notification_data).encode("utf-8")
        ).decode("utf-8")

        payload = {
            "message": {
                "data": encoded_data,
                "messageId": "test_refund_notification_processing",
            },
            "subscription": "projects/openedx-mobile/subscriptions/playRefundSubscriptionPush",
        }

        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify signal was sent with correct parameters
        mock_payment_refunded_signal.send_robust.assert_called_once()
        args = mock_payment_refunded_signal.send_robust.call_args
        self.assertEqual(args[1]["payment_interface"], "android_iap_edx")
        refund = args[1]["refund"]
        self.assertEqual(refund["id"], "GPA.3388-4288-9788-12345")
        self.assertEqual(refund["created"], "1746057600000")
        self.assertEqual(refund["status"], "succeeded")
        self.assertEqual(refund["amount"], "UNSET")
        self.assertEqual(refund["currency"], "UNSET")

    @mock.patch("commerce_coordinator.apps.iap.views.payment_refunded_signal")
    def test_non_refund_notification(self, mock_payment_refunded_signal):
        """Test handling of non-refund notifications."""
        notification_data = {
            **self.base_notification_data,
            "testNotification": {"message": "Test message"},
        }
        encoded_data = base64.b64encode(
            json.dumps(notification_data).encode("utf-8")
        ).decode("utf-8")

        payload = {
            "message": {
                "data": encoded_data,
                "messageId": "test_non_refund_notification",
            },
            "subscription": "projects/openedx-mobile/subscriptions/playRefundSubscriptionPush",
        }

        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_payment_refunded_signal.send_robust.assert_not_called()

    @mock.patch("commerce_coordinator.apps.iap.views.payment_refunded_signal")
    def test_refund_type_check(self, mock_payment_refunded_signal):
        """Test refund type validation."""
        notification_data = {
            **self.base_notification_data,
            "voidedPurchaseNotification": {
                "orderId": "GPA.3388-4288-9788-12345",
                "refundType": 2,  # 2 is for partial refund
            },
        }
        encoded_data = base64.b64encode(
            json.dumps(notification_data).encode("utf-8")
        ).decode("utf-8")

        payload = {
            "message": {
                "data": encoded_data,
                "messageId": "test_refund_type_check",
            },
            "subscription": "projects/openedx-mobile/subscriptions/playRefundSubscriptionPush",
        }

        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_payment_refunded_signal.send_robust.assert_not_called()

    @mock.patch("commerce_coordinator.apps.iap.views.payment_refunded_signal")
    def test_subscription_type_check(self, mock_payment_refunded_signal):
        """Test subscription type validation."""
        payload = {
            "message": {
                "data": {},
                "messageId": "test_subscription_type_check",
            },
            "subscription": "wrongSubscription",
        }

        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_payment_refunded_signal.send_robust.assert_not_called()
