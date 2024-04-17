"""
Tests for the frontend_app_ecommerce app views.
"""

import ddt
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from mock import patch
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from commerce_coordinator.apps.frontend_app_ecommerce.tests import (
    ECOMMERCE_REQUEST_EXPECTED_RESPONSE,
    ORDER_HISTORY_GET_PARAMETERS,
    CTOrdersForCustomerMock,
    EcommerceClientMock
)
from commerce_coordinator.apps.frontend_app_ecommerce.tests.conftest import (
    gen_order_for_payment_intent,
    gen_payment_intent
)

User = get_user_model()


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
        self.assertEqual(response.json()['results'][1], ECOMMERCE_REQUEST_EXPECTED_RESPONSE['results'][0])

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

        self.user = User.objects.create_user(
            self.test_user_username,
            self.test_user_email,
            self.test_user_password,
            is_staff=True,
            lms_user_id=127
        )

    def tearDown(self):
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
        self.assertTrue(response.headers['Location'].startswith('http://localhost'))
        self.assertTrue(response.headers['Location'].endswith(order_number))

    def test_view_404s_when_no_order_number(self):
        self.client.login(username=self.test_user_username, password=self.test_user_password)
        response = self.client.get(self.url, data={})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('commerce_coordinator.apps.stripe.clients.StripeAPIClient.retrieve_payment_intent')
    @patch('commerce_coordinator.apps.commercetools.pipeline.CommercetoolsAPIClient')
    def test_view_303s_when_order_number_might_be_ct(self, ct_mock, stripe_mock):
        intent = gen_payment_intent()
        order = gen_order_for_payment_intent()

        ct_mock.return_value.get_order_by_id.return_value = order
        stripe_mock.return_value = intent

        order_number = 'EDX-ZZZ001'
        self.client.login(username=self.test_user_username, password=self.test_user_password)
        response = self.client.get(self.url, data={'order_number': order_number})
        self.assertEqual(response.status_code, status.HTTP_303_SEE_OTHER)

    @patch('commerce_coordinator.apps.stripe.clients.StripeAPIClient.retrieve_payment_intent')
    @patch('commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_order_by_id')
    def test_view_forwards_to_stripe_receipt_page(self, ct_mock, stripe_mock):
        intent = gen_payment_intent()
        order = gen_order_for_payment_intent()

        ct_mock.return_value = order
        stripe_mock.return_value = intent

        order_number = order.id
        self.client.login(username=self.test_user_username, password=self.test_user_password)

        response = self.client.get(self.url, data={'order_number': order_number})
        self.assertEqual(response.status_code, status.HTTP_303_SEE_OTHER)
        self.assertEqual(response.headers['Location'], intent.latest_charge.receipt_url)

    @override_settings(
        OPEN_EDX_FILTERS_CONFIG={
            "org.edx.coordinator.frontend_app_ecommerce.order.receipt_url.requested.v1": {
                "fail_silently": False,
                "pipeline": [
                    'commerce_coordinator.apps.rollout.pipeline.DetermineActiveOrderManagementSystemByOrder',
                    'commerce_coordinator.apps.commercetools.pipeline.FetchOrderDetails',
                    'commerce_coordinator.apps.stripe.pipeline.GetPaymentIntentReceipt'
                ]
            },
        },
    )
    def test_view_forwards_ct_pipe_system_check(self):
        order_number = 'EDX-999999'
        self.client.login(username=self.test_user_username, password=self.test_user_password)

        response = self.client.get(self.url, data={'order_number': order_number})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('commerce_coordinator.apps.stripe.clients.StripeAPIClient.retrieve_payment_intent')
    @patch('commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_order_by_id')
    def test_view_errors_if_ct_order_has_no_intent_id(self, ct_mock, stripe_mock):
        intent = gen_payment_intent()
        order = gen_order_for_payment_intent()

        for pr in order.payment_info.payments:
            pmt = pr.obj
            pmt.payment_status.interface_code = "meow"

        ct_mock.return_value = order
        stripe_mock.return_value = intent

        order_number = order.id
        self.client.login(username=self.test_user_username, password=self.test_user_password)

        response = self.client.get(self.url, data={'order_number': order_number})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
