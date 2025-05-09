"""Test suite for the CreateOrderView in the IAP API."""

from unittest.mock import MagicMock, patch
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture(name="test_user")
def fixture_test_user():
    """Returns a mock user with ID and customer ID."""
    mock_user = MagicMock()
    mock_user.id = "user-id"
    mock_user.customer_id = "customer-id"
    return mock_user


@pytest.fixture(name="authed_api_client")
def fixture_authed_api_client(test_user):
    """Returns an authenticated APIClient."""
    client = APIClient()
    client.force_authenticate(user=test_user)
    return client


@pytest.mark.django_db
class TestCreateOrderView:
    """Test cases for CreateOrderView."""

    @patch("commerce_coordinator.apps.iap.api.v1.views.CommercetoolsAPIClient")
    def test_create_order_success(self, mock_ct_client_class, authed_api_client):
        mock_cart = MagicMock(id="cart-id", version=1, customer_id="customer-id",
                              total_price={"centAmount": 1000, "currencyCode": "USD"},
                              cart_state="Active", line_items=[])

        mock_payment = MagicMock(id="payment-id")
        mock_payment.payment_status = MagicMock(interface_code="APPROVED", state=None)

        mock_order = MagicMock(id="order-id", version=1, order_number="ORDER123", line_items=[])

        mock_ct_client = MagicMock()
        mock_ct_client.base_client.carts.get_by_id.return_value = mock_cart
        mock_ct_client.base_client.payments.create.return_value = mock_payment
        mock_ct_client.base_client.carts.update_by_id.return_value = mock_cart
        mock_ct_client.base_client.orders.create.return_value = mock_order
        mock_ct_client.base_client.orders.update_by_id.return_value = mock_order

        mock_ct_client_class.return_value = mock_ct_client

        url = reverse("iap:v1:create_order")
        response = authed_api_client.post(url, {
            "cart_id": "cart-id",
            "order_number": "ORDER123",
            "payment_method": "paypal"
        }, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["order_id"] == "order-id"
        assert response.data["order_number"] == "ORDER123"
        assert response.data["payment_status"] == "APPROVED"

    def test_invalid_input_returns_400(self, authed_api_client):
        url = reverse("iap:v1:create_order")
        response = authed_api_client.post(url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("commerce_coordinator.apps.iap.api.v1.views.CommercetoolsAPIClient")
    def test_cart_not_belonging_to_user_returns_403(self, mock_ct_client_class, authed_api_client):
        mock_cart = MagicMock(id="cart-id", customer_id="other-user-id", cart_state="Active")

        mock_ct_client = MagicMock()
        mock_ct_client.base_client.carts.get_by_id.return_value = mock_cart
        mock_ct_client_class.return_value = mock_ct_client

        url = reverse("iap:v1:create_order")
        response = authed_api_client.post(url, {
            "cart_id": "cart-id",
            "order_number": "ORDER123",
            "payment_method": "paypal"
        }, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("commerce_coordinator.apps.iap.api.v1.views.CommercetoolsAPIClient")
    def test_cart_not_active_returns_400(self, mock_ct_client_class, authed_api_client):
        mock_cart = MagicMock(id="cart-id", customer_id="customer-id", cart_state="Frozen")

        mock_ct_client = MagicMock()
        mock_ct_client.base_client.carts.get_by_id.return_value = mock_cart
        mock_ct_client_class.return_value = mock_ct_client

        url = reverse("iap:v1:create_order")
        response = authed_api_client.post(url, {
            "cart_id": "cart-id",
            "order_number": "ORDER123",
            "payment_method": "paypal"
        }, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("commerce_coordinator.apps.iap.api.v1.views.set_shipping_address")
    @patch("commerce_coordinator.apps.iap.api.v1.views.CommercetoolsAPIClient")
    def test_invalid_shipping_address_returns_400(
        self, mock_ct_client_class, mock_set_shipping_address, authed_api_client
    ):
        mock_cart = MagicMock(id="cart-id", customer_id="customer-id", cart_state="Active")
        mock_set_shipping_address.side_effect = ValueError("Invalid address")

        mock_ct_client = MagicMock()
        mock_ct_client.base_client.carts.get_by_id.return_value = mock_cart
        mock_ct_client_class.return_value = mock_ct_client

        url = reverse("iap:v1:create_order")
        response = authed_api_client.post(url, {
            "cart_id": "cart-id",
            "order_number": "ORDER123",
            "payment_method": "paypal",
            "shipping_address": {"streetName": "Fake St"}
        }, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("commerce_coordinator.apps.iap.api.v1.views.CommercetoolsAPIClient")
    def test_payment_creation_failure_returns_500(self, mock_ct_client_class, authed_api_client):
        mock_cart = MagicMock(
            id="cart-id",
            customer_id="customer-id",
            cart_state="Active",
            total_price={"centAmount": 1000, "currencyCode": "USD"}
        )

        mock_ct_client = MagicMock()
        mock_ct_client.base_client.carts.get_by_id.return_value = mock_cart
        mock_ct_client.base_client.payments.create.side_effect = Exception("Failed to create payment")
        mock_ct_client_class.return_value = mock_ct_client

        url = reverse("iap:v1:create_order")
        response = authed_api_client.post(url, {
            "cart_id": "cart-id",
            "order_number": "ORDER123",
            "payment_method": "paypal"
        }, format="json")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
