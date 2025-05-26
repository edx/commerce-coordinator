"""
Tests for the InAppPurchase app views.
"""

import datetime
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
    @mock.patch("uuid.uuid4")
    def test_successful_order_creation(
        self,
        mock_uuid,
        mock_get_edx_lms_user_id,
        mock_get_email_domain,
        mock_get_standalone_price,
        mock_get_ct_customer,
        *args,
    ):
        mock_ct_client = args[-1]
        self.authenticate_user()
        mock_uuid.return_value = "test-uuid"

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

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
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

    @mock.patch("commerce_coordinator.apps.iap.views.ServiceAccountCredentials")
    @mock.patch("commerce_coordinator.apps.iap.views.payment_refunded_signal")
    @mock.patch("commerce_coordinator.apps.iap.views.settings")
    @mock.patch("commerce_coordinator.apps.iap.views.build")
    @mock.patch("commerce_coordinator.apps.iap.views.datetime")
    def test_voided_purchases_processing(
        self,
        mock_datetime,
        mock_build,
        mock_settings,
        mock_payment_refunded_signal,
        _,
    ):
        """Test processing of voided purchases."""
        mock_settings.PAYMENT_PROCESSOR_CONFIG = {
            "android_iap": {
                "refunds_age_in_days": 3,
                "google_bundle_id": "org.edx.mobile",
                "google_service_account_key_file": {"key": "value"},
                "google_publisher_api_scope": [
                    "https://www.googleapis.com/auth/androidpublisher"
                ],
            }
        }
        mock_date = datetime.datetime(2025, 5, 2, 0, 0, 0)
        mock_datetime.datetime.now.return_value = mock_date
        mock_datetime.timedelta = datetime.timedelta

        mock_service = mock.MagicMock()
        mock_purchases = mock.MagicMock()
        mock_voided_purchases = mock.MagicMock()
        mock_list = mock.MagicMock()
        mock_service.purchases.return_value = mock_purchases
        mock_purchases.voidedpurchases.return_value = mock_voided_purchases
        mock_voided_purchases.list.return_value = mock_list
        mock_build.return_value = mock_service
        mock_list.execute.return_value = {
            "voidedPurchases": [
                {
                    "orderId": "GPA.1234-5432-1098-76543",
                    "voidedReason": 0,
                    "voidedSource": 1,
                    "voidedTimeMillis": "1746057600000",  # May 1, 2025
                },
                {
                    "orderId": "GPA.9876-5432-1098-76543",
                    "voidedReason": 0,
                    "voidedSource": 1,
                    "voidedTimeMillis": "1748736000000",  # June 1, 2025
                },
            ]
        }

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify API was called correctly
        expected_timestamp = 1745884800000
        mock_voided_purchases.list.assert_called_once_with(
            packageName="org.edx.mobile", startTime=expected_timestamp
        )

        # Verify signals were sent for each voided purchase
        self.assertEqual(mock_payment_refunded_signal.send_robust.call_count, 2)

        # Verify first refund
        first_call = mock_payment_refunded_signal.send_robust.call_args_list[0]
        self.assertEqual(first_call[1]["payment_interface"], "android_iap_edx")
        first_refund = first_call[1]["refund"]
        self.assertEqual(first_refund["id"], "GPA.1234-5432-1098-76543")
        self.assertEqual(first_refund["created"], "1746057600000")  # May 1, 2025
        self.assertEqual(first_refund["status"], "succeeded")

        # Verify second refund
        second_call = mock_payment_refunded_signal.send_robust.call_args_list[1]
        self.assertEqual(second_call[1]["payment_interface"], "android_iap_edx")
        second_refund = second_call[1]["refund"]
        self.assertEqual(second_refund["id"], "GPA.9876-5432-1098-76543")
        self.assertEqual(second_refund["created"], "1748736000000")  # June 1, 2025
