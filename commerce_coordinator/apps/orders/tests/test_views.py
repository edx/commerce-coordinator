"""
Tests for the orders app views.
"""
import logging
from unittest.mock import MagicMock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from mock import patch
from rest_framework.test import APIClient

from commerce_coordinator.apps.orders.tests import ECOMMERCE_REQUEST_EXPECTED_RESPONSE, ECOMMERCE_REQUEST_GET_PARAMETERS

logger = logging.getLogger(__name__)


class EcommerceClientMock(MagicMock):
    """A mock EcommerceApiClient that always returns ECOMMERCE_REQUEST_EXPECTED_RESPONSE."""
    return_value = ECOMMERCE_REQUEST_EXPECTED_RESPONSE


@patch('commerce_coordinator.apps.orders.clients.EcommerceApiClient.get_orders', new_callable=EcommerceClientMock)
class OrdersEcommerceViewsTests(TestCase):
    """
    Tests for Ecommerce order views.
    """
    # Disable unused-argument due to global @patch
    # pylint: disable=unused-argument

    # Use Django Rest Framework client for self.client
    client_class = APIClient

    # Define test user properties
    test_user_username = 'test'  # Different from ECOMMERCE_REQUEST_GET_PARAMETERS username.
    test_user_email = 'test@example.com'
    test_user_password = 'secret'

    def setUp(self):
        """Create test user before test starts."""

        super().setUp()
        User = get_user_model()
        User.objects.create_user(self.test_user_username, self.test_user_email, self.test_user_password)

    def tearDown(self):
        """Log out any user from client after test ends."""

        super().tearDown()
        self.client.logout()

    def test_ecommerce_view_rejects_post(self, mock_ecommerce_client):
        """Check POST from authorized user receives a 405 Method Not Allowed."""

        # Login
        self.client.login(username=self.test_user_username, password=self.test_user_password)

        # Perform POST
        response = self.client.post(reverse('orders:order_history'), ECOMMERCE_REQUEST_GET_PARAMETERS)

        # Check 405 Method Not Allowed
        self.assertEqual(response.status_code, 405)

    def test_ecommerce_view_rejects_unauthorized(self, mock_ecommerce_client):
        """Check unauthorized users querying orders are redirected to login page."""

        # Perform GET without logging in.
        response = self.client.get(reverse('orders:order_history'), ECOMMERCE_REQUEST_GET_PARAMETERS)

        # Check 302 Found with redirect to login page.
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.url)

    def test_ecommerce_view_returns_ok(self, mock_ecommerce_client):
        """Check authorized user querying orders receives an HTTP 200 OK."""

        # Login
        self.client.login(username=self.test_user_username, password=self.test_user_password)

        # Perform GET
        response = self.client.get(reverse('orders:order_history'), ECOMMERCE_REQUEST_GET_PARAMETERS)

        # Check 200 OK
        self.assertEqual(response.status_code, 200)

    def test_ecommerce_view_returns_expected_response(self, mock_ecommerce_client):
        """Check authorized user querying orders receive an expected response."""

        # Login
        self.client.login(username=self.test_user_username, password=self.test_user_password)

        # Perform GET
        response = self.client.get(reverse('orders:order_history'), ECOMMERCE_REQUEST_GET_PARAMETERS)

        # Check expected response
        self.assertEqual(response.json(), ECOMMERCE_REQUEST_EXPECTED_RESPONSE)

    def test_ecommerce_view_passes_username(self, mock_ecommerce_client):
        """Check logged in user's username is passed to the ecommerce client."""

        # Login
        self.client.login(username=self.test_user_username, password=self.test_user_password)

        # Perform GET
        self.client.get(reverse('orders:order_history'), ECOMMERCE_REQUEST_GET_PARAMETERS)

        # Get username sent to ecommerce client
        request_username = mock_ecommerce_client.call_args.args[0]['username']

        # Check username is passed to ecommerce client
        self.assertEqual(request_username, self.test_user_username)
