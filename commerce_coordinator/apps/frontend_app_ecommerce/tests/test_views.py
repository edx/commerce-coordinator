"""
Tests for the frontend_app_ecommerce app views.
"""
import logging

import ddt
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from mock import patch
from openedx_filters.exceptions import OpenEdxFilterException
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from commerce_coordinator.apps.commercetools.tests.conftest import APITestingSet
from commerce_coordinator.apps.core.tests.utils import uuid4_str
from commerce_coordinator.apps.frontend_app_ecommerce.tests import (
    ECOMMERCE_REQUEST_EXPECTED_RESPONSE,
    ORDER_HISTORY_GET_PARAMETERS,
    CTOrdersForCustomerMock,
    EcommerceClientMock
)

logger = logging.getLogger(__name__)

User = get_user_model()

TEST_ECOMMERCE_URL = 'https://testserver.com'


@patch('commerce_coordinator.apps.ecommerce.clients.EcommerceAPIClient.get_orders',
       new_callable=EcommerceClientMock)
@patch(
    'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_orders_for_customer',
    new_callable=CTOrdersForCustomerMock
)
class OrdersViewTests(TestCase):
    """
    Tests for order views.
    """
    # Disable unused-argument due to global @patch

    # Use Django Rest Framework client for self.client
    client_class = APIClient

    # Define test user properties
    test_user_username = 'test'  # Different from ORDER_HISTORY_GET_PARAMETERS username.
    test_user_email = 'test@example.com'
    test_user_password = 'secret'

    def setUp(self):
        """Create test user before test starts."""

        super().setUp()
        User.objects.create_user(
            self.test_user_username,
            self.test_user_email,
            self.test_user_password,
            lms_user_id=127
        )

    def tearDown(self):
        """Log out any user from client after test ends."""

        super().tearDown()
        self.client.logout()

    def test_view_rejects_post(self, _mock_ctorders, _mock_ecommerce_client):
        """Check POST from authorized user receives a 405 Method Not Allowed."""

        # Login
        self.client.login(username=self.test_user_username, password=self.test_user_password)

        # Perform POST
        response = self.client.post(reverse('frontend_app_ecommerce:order_history'), ORDER_HISTORY_GET_PARAMETERS)

        # Check 405 Method Not Allowed
        self.assertEqual(response.status_code, 405)

    def test_view_rejects_unauthorized(self, _mock_ctorders, _mock_ecommerce_client):
        """Check unauthorized users querying orders are redirected to login page."""

        # Perform GET without logging in.
        response = self.client.get(reverse('frontend_app_ecommerce:order_history'), ORDER_HISTORY_GET_PARAMETERS)

        # Check 302 Found with redirect to login page.
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.url)

    def test_view_returns_ok(self, _mock_ctorders, _mock_ecommerce_client):
        """Check authorized user querying orders receives an HTTP 200 OK."""

        # Login
        self.client.login(username=self.test_user_username, password=self.test_user_password)

        # Perform GET
        response = self.client.get(reverse('frontend_app_ecommerce:order_history'), ORDER_HISTORY_GET_PARAMETERS)
        # Check 200 OK
        self.assertEqual(response.status_code, 200)

    def test_view_returns_expected_ecommerce_response(self, _mock_ctorders, _mock_ecommerce_client):
        """Check authorized user querying orders receive an expected response."""

        # Login
        self.client.login(username=self.test_user_username, password=self.test_user_password)

        # Perform GET
        response = self.client.get(reverse('frontend_app_ecommerce:order_history'), ORDER_HISTORY_GET_PARAMETERS)

        # Check expected response
        self.assertEqual(response.json()[1], ECOMMERCE_REQUEST_EXPECTED_RESPONSE['results'][0])

    def test_view_passes_username(self, _mock_ctorders, mock_ecommerce_client):
        """Check logged in user's username is passed to the ecommerce client."""

        # Login
        self.client.login(username=self.test_user_username, password=self.test_user_password)

        # Perform GET
        self.client.get(reverse('frontend_app_ecommerce:order_history'), ORDER_HISTORY_GET_PARAMETERS)

        # Get username sent to ecommerce client
        request_username = mock_ecommerce_client.call_args.args[0]['username']

        # Check username is passed to ecommerce client
        self.assertEqual(request_username, self.test_user_username)


@override_settings(BACKEND_SERVICE_EDX_OAUTH2_PROVIDER_URL='https://testserver.com/auth')
@ddt.ddt
class ReceiptRedirectViewTests(APITestCase):
    """
    Tests for payment page redirect view.
    """
    # Define test user properties
    test_user_username = 'test'
    test_user_email = 'test@example.com'
    test_user_password = 'secret'
    url = reverse('frontend_app_ecommerce:order_receipt')

    def setUp(self):
        super().setUp()
        self.client_set = APITestingSet.new_instance()

        self.user = User.objects.create_user(
            self.test_user_username,
            self.test_user_email,
            self.test_user_password,
            is_staff=True,
            lms_user_id=127
        )

    def tearDown(self):
        # force deconstructor call or some test get flaky
        del self.client_set
        super().tearDown()
        self.client.logout()

    def test_view_rejects_unauthorized(self):
        """Check unauthorized users querying orders are redirected to login page."""
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)

    def test_view_sends_to_legacy_ecommerce(self):
        order_number = 'EDX-100001'
        self.client.login(username=self.test_user_username, password=self.test_user_password)
        response = self.client.get(self.url, data={'order_number': order_number})

        self.assertEqual(response.status_code, status.HTTP_303_SEE_OTHER)
        self.assertTrue(response.url.startswith('http://localhost'))
        self.assertTrue(response.url.endswith(order_number))

    def test_view_404s_when_bad_order_number(self):
        order_number = 'EDX-ZZZ001'
        self.client.login(username=self.test_user_username, password=self.test_user_password)
        with self.assertRaises(OpenEdxFilterException):
            _ = self.client.get(self.url, data={'order_number': order_number})

    def test_view_forwards_to_stripe_receipt_page(self):
        # TODO: GRM: Mock out Payment Intent Response
        # TODO: GRM: Mock out Commercetools
        order_number = uuid4_str()
        self.client.login(username=self.test_user_username, password=self.test_user_password)
        response = self.client.get(self.url, data={'order_number': order_number})
        self.assertEqual(response.status_code, status.HTTP_303_SEE_OTHER)
        breakpoint()
