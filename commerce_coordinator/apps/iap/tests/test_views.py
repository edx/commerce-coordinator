"""
Tests for the InAppPurchase app views.
"""

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
        self.ct_client_patcher = mock.patch(
            "commerce_coordinator.apps.iap.views.CommercetoolsAPIClient"
        )
        self.get_ct_customer_patcher = mock.patch(
            "commerce_coordinator.apps.iap.views.get_ct_customer"
        )
        self.get_standalone_price_patcher = mock.patch(
            "commerce_coordinator.apps.iap.views.get_standalone_price_for_sku"
        )
        self.get_email_domain_patcher = mock.patch(
            "commerce_coordinator.apps.iap.views.get_email_domain"
        )
        self.get_edx_lms_user_id_patcher = mock.patch(
            "commerce_coordinator.apps.iap.views.get_edx_lms_user_id"
        )
        self.segment_event_tracker_patcher = mock.patch(
            "commerce_coordinator.apps.iap.views.SegmentEventTracker"
        )
        self.mock_ct_client = self.ct_client_patcher.start()
        self.mock_get_ct_customer = self.get_ct_customer_patcher.start()
        self.mock_get_standalone_price = self.get_standalone_price_patcher.start()
        self.mock_get_email_domain = self.get_email_domain_patcher.start()
        self.mock_get_edx_lms_user_id = self.get_edx_lms_user_id_patcher.start()
        self.mock_segment_event_tracker = self.segment_event_tracker_patcher.start()

        self.addCleanup(self.ct_client_patcher.stop)
        self.addCleanup(self.get_ct_customer_patcher.stop)
        self.addCleanup(self.get_standalone_price_patcher.stop)
        self.addCleanup(self.get_email_domain_patcher.stop)
        self.addCleanup(self.get_edx_lms_user_id_patcher.stop)
        self.addCleanup(self.segment_event_tracker_patcher.stop)

        self.mock_ct_client.return_value.get_new_order_number.return_value = (
            "ORDER-123"
        )
        self.mock_get_email_domain.return_value = "example.com"
        self.mock_get_standalone_price.return_value = Money(
            cent_amount=4999, currency_code="USD"
        )
        self.mock_get_edx_lms_user_id.return_value = 12345

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

    def test_view_rejects_unauthorized(self):
        self.client.logout()
        response = self.client.post(self.url, self.valid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_post_with_invalid_data_fails(self):
        self.authenticate_user()
        response = self.client.post(self.url, self.invalid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch("uuid.uuid4")
    def test_successful_order_creation(self, mock_uuid):
        self.authenticate_user()
        mock_uuid.return_value = "test-uuid"

        mock_customer = mock.MagicMock()
        mock_customer.id = "customer-123"
        mock_customer.email = self.test_user_email
        self.mock_get_ct_customer.return_value = mock_customer

        mock_cart = mock.MagicMock()
        mock_cart.id = "cart-123"
        self.mock_ct_client.return_value.get_customer_cart.return_value = None
        self.mock_ct_client.return_value.create_cart.return_value = mock_cart

        mock_payment = mock.MagicMock()
        mock_payment.id = "payment-123"
        self.mock_ct_client.return_value.create_payment.return_value = mock_payment

        mock_order = mock.MagicMock()
        mock_order.id = "order-123"
        mock_order.order_number = "ORDER-123"
        mock_order.version = 1
        mock_line_item = mock.MagicMock()
        mock_line_item.state = [mock.MagicMock(state=mock.MagicMock(id="state-123"))]
        mock_order.line_items = [mock_line_item]
        self.mock_ct_client.return_value.create_order_from_cart.return_value = (
            mock_order
        )
        self.mock_ct_client.return_value.update_line_items_transition_state.return_value = (
            mock_order
        )

        response = self.client.post(self.url, self.valid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data, {"order_id": "order-123", "order_number": "ORDER-123"}
        )

    def test_commercetools_error_handling(self):
        """Test handling of CommercetoolsError."""
        self.authenticate_user()
        self.mock_ct_client.return_value.get_customer_cart.side_effect = (
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
    def test_invalid_request_variations(self, invalid_data):
        """Test various invalid request scenarios."""
        self.authenticate_user()
        payload = self.valid_payload.copy()
        payload.update(invalid_data)

        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
