"""Tests for the commercetools views"""

from unittest.mock import MagicMock, patch

import ddt
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from commerce_coordinator.apps.commercetools.tests.conftest import gen_customer, gen_order
from commerce_coordinator.apps.commercetools.tests.constants import (
    EXAMPLE_COMMERCETOOLS_ORDER_FULFILL_MESSAGE,
    EXAMPLE_COMMERCETOOLS_ORDER_SANCTIONED_MESSAGE,
    EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD
)
from commerce_coordinator.apps.core.models import User


class FulfillOrderPlacedSignalMock(MagicMock):
    """
    A mock fulfill_order_placed_signal that always returns
    EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD in the shape of format_signal_results.
    """

    def mock_receiver(self):
        pass  # pragma: no cover

    return_value = [
        (mock_receiver, 'bogus_task_id'),
    ]


class CTOrderByIdMock(MagicMock):
    """
    A mock get_order_by_id call that always returns
    EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD in the shape of format_signal_results.
    """
    return_value = gen_order(EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD['order_number'])


class CTCustomerByIdMock(MagicMock):
    """
    A mock get_customer_by_id call that always returns
    EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD in the shape of format_signal_results.
    """
    return_value = gen_customer("hiya@text.example", "jim_34")


@ddt.ddt
@patch('commerce_coordinator.apps.commercetools.views.fulfill_order_placed_signal.send_robust',
       new_callable=FulfillOrderPlacedSignalMock)
@patch(
        'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_order_by_id',
        new_callable=CTOrderByIdMock
    )
@patch(
        'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_customer_by_id',
        new_callable=CTCustomerByIdMock
    )
class OrderFulfillViewTests(APITestCase):
    # Disable unused-argument due to global @patch
    # pylint: disable=unused-argument
    "Tests for order fulfill view"
    url = reverse('commercetools:fulfill')

    # Use Django Rest Framework client for self.client
    client_class = APIClient

    # Define test user properties
    test_user_username = 'test_user'
    test_staff_username = 'test_staff_user'
    test_password = 'test_password'

    def setUp(self):
        """Create test user before test starts."""

        super().setUp()

        User.objects.create_user(username=self.test_user_username, password=self.test_password)
        User.objects.create_user(username=self.test_staff_username, password=self.test_password,  is_staff=True)

    def tearDown(self):
        """Log out any user from client after test ends."""

        super().tearDown()
        self.client.logout()

    def test_view_returns_ok(self, mock_customer, mock_order, mock_signal):
        """Check authorized user requesting fulfillment receives a HTTP 200 OK."""

        # Login
        self.client.login(username=self.test_staff_username, password=self.test_password)

        # Send request
        response = self.client.post(self.url, data=EXAMPLE_COMMERCETOOLS_ORDER_FULFILL_MESSAGE, format='json')

        # Check 200 OK
        self.assertEqual(response.status_code, 200)

    def test_view_sends_expected_signal_parameters(self, mock_customer, mock_order, mock_signal):
        """Check view sends expected signal parameters."""
        # Login
        self.client.login(username=self.test_staff_username, password=self.test_password)

        # Send request
        self.client.post(self.url, data=EXAMPLE_COMMERCETOOLS_ORDER_FULFILL_MESSAGE, format='json')

        # Check expected response
        mock_signal.assert_called_once_with(**EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD)

    @patch("commerce_coordinator.apps.commercetools.views.send_order_confirmation_email")
    def test_view_triggers_order_confirmation_email(self, mock_send_email, mock_customer, mock_order, mock_signal):
        """Check view sends expected signal parameters."""
        self.client.login(username=self.test_staff_username, password=self.test_password)

        self.client.post(self.url, data=EXAMPLE_COMMERCETOOLS_ORDER_FULFILL_MESSAGE, format='json')

        mock_send_email.assert_called_once()

    def test_view_returns_expected_error(self, mock_customer, mock_order, mock_signal):
        """Check authorized account requesting fulfillment with bad inputs receive an expected error."""

        # Login
        self.client.login(username=self.test_staff_username, password=self.test_password)

        # Add errors to example request
        payload_with_errors = EXAMPLE_COMMERCETOOLS_ORDER_FULFILL_MESSAGE.copy()
        payload_with_errors.pop('detail')

        # Send request
        response = self.client.post(self.url, data=payload_with_errors, format='json')

        # Check expected response
        expected_response = {
            'detail': ['This field is required.'],
        }
        self.assertEqual(response.json(), expected_response)

    def test_view_returns_expected_error_no_order(self, mock_customer, mock_order, mock_signal):
        """Check authorized account requesting fulfillment unable to get customer receive an expected error."""
        mock_customer.return_value = None
        # Login
        self.client.login(username=self.test_staff_username, password=self.test_password)

        # Send request
        response = self.client.post(self.url, data=EXAMPLE_COMMERCETOOLS_ORDER_FULFILL_MESSAGE, format='json')

        self.assertEqual(response.status_code, 200)


@ddt.ddt
@patch(
    'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_order_by_id',
    new_callable=CTOrderByIdMock
)
@patch(
    'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_customer_by_id',
    new_callable=CTCustomerByIdMock
)
class OrderSanctionedViewTests(APITestCase):
    # Disable unused-argument due to global @patch
    # pylint: disable=unused-argument
    "Tests for order sanctioned view"
    url = reverse('commercetools:sanctioned')

    # Use Django Rest Framework client for self.client
    client_class = APIClient

    test_user_username = 'test_user'
    test_staff_username = 'test_staff_user'
    test_password = 'test_password'

    def setUp(self):
        """Create test user before test starts."""

        super().setUp()

        User.objects.create_user(username=self.test_user_username, password=self.test_password)
        User.objects.create_user(username=self.test_staff_username, password=self.test_password,  is_staff=True)

    def tearDown(self):
        """Log out any user from client after test ends."""

        super().tearDown()
        self.client.logout()

    def test_view_returns_ok(self, mock_customer, mock_order):
        """Check authorized user requesting sanction receives a HTTP 200 OK."""

        # Login
        self.client.login(username=self.test_staff_username, password=self.test_password)

        # Send request
        response = self.client.post(self.url, data=EXAMPLE_COMMERCETOOLS_ORDER_SANCTIONED_MESSAGE, format='json')

        # Check 200 OK
        self.assertEqual(response.status_code, 200)

    def test_view_returns_expected_error(self, mock_customer, mock_order):
        """Check authorized account requesting fulfillment with bad inputs receive an expected error."""

        # Login
        self.client.login(username=self.test_staff_username, password=self.test_password)

        # Add errors to example request
        payload_with_errors = EXAMPLE_COMMERCETOOLS_ORDER_SANCTIONED_MESSAGE.copy()
        payload_with_errors.pop('detail')

        # Send request
        response = self.client.post(self.url, data=payload_with_errors, format='json')

        # Check expected response
        expected_response = {
            'detail': ['This field is required.'],
        }
        self.assertEqual(response.json(), expected_response)

    def test_view_returns_expected_error_no_order(self, mock_customer, mock_order):
        """Check authorized account requesting fulfillment unable to get customer receive an expected error."""
        mock_customer.return_value = None
        # Login
        self.client.login(username=self.test_staff_username, password=self.test_password)

        # Send request
        response = self.client.post(self.url, data=EXAMPLE_COMMERCETOOLS_ORDER_SANCTIONED_MESSAGE, format='json')

        self.assertEqual(response.status_code, 200)

# """ Commercetools Order History testcases """
# from unittest.mock import MagicMock, patch
#
# from django.contrib.auth import get_user_model
# from django.urls import reverse
# from rest_framework.test import APITestCase
#
# from commerce_coordinator.apps.commercetools.clients import PaginatedResult
# from commerce_coordinator.apps.commercetools.tests.conftest import gen_order
# from commerce_coordinator.apps.commercetools.tests.test_data import gen_customer
# from commerce_coordinator.apps.core.tests.utils import uuid4_str
# from commerce_coordinator.apps.frontend_app_ecommerce.tests.test_views import EcommerceClientMock
#
# User = get_user_model()
#
# orders = [gen_order(uuid4_str())]
#
#
# class CTOrdersForCustomerMock(MagicMock):
#     """A mock EcommerceAPIClient that always returns ECOMMERCE_REQUEST_EXPECTED_RESPONSE."""
#     return_value = (
#         PaginatedResult(orders, len(orders), 0),
#         gen_customer(email='test@example.com', un="test")
#     )
#
#
# class OrderHistoryViewTests(APITestCase):
#     """
#     Tests for order history view
#     """
#
#     # Define test user properties
#     test_user_username = 'test'
#     test_user_email = 'test@example.com'
#     test_user_password = 'secret'
#     url = reverse('commercetools:order_history')
#
#     def setUp(self):
#         """Create test user before test starts."""
#         super().setUp()
#         self.user = User.objects.create_user(
#             self.test_user_username,
#             self.test_user_email,
#             self.test_user_password,
#             lms_user_id=127,
#             # TODO: Remove is_staff=True
#             is_staff=True,
#         )
#
#     def tearDown(self):
#         """Log out any user from the client after test ends."""
#         super().tearDown()
#         self.client.logout()
#
#     @patch(
#         'commerce_coordinator.apps.ecommerce.clients.EcommerceAPIClient.get_orders',
#         new_callable=EcommerceClientMock
#     )
#     @patch(
#         'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_orders_for_customer',
#         new_callable=CTOrdersForCustomerMock
#     )
#     def test_order_history_functional(self, _, __):
#         """Happy path test function for CT Order History"""
#         self.client.force_authenticate(user=self.user)
#         query_params = {}  # we don't accept any rn
#
#         response = self.client.get(self.url, data=query_params)
#         self.assertEqual(response.status_code, 200)
#
#         response_json: dict = response.json()
#
#         self.assertIn('order_data', response_json.keys())
#         self.assertEqual(2, len(response_json['order_data']))
#         # because of how the dates work within this test the old system value should be second as its date is older
#         self.assertEqual(response_json['order_data'][1]['payment_processor'], 'cybersource-rest')
#
#     def test_order_history_denied(self):
#         """bad/incomplete auth test function for CT Order History"""
#
#         self.client.force_authenticate(user=User.objects.create_user(
#                 "joey",
#                 "something@something.com",
#                 "shh its @ secret!",
#                 # TODO: Remove is_staff=True
#                 is_staff=True,
#             ))
#         query_params = {}  # we don't accept any rn
#
#         response = self.client.get(self.url, data=query_params)
#         self.assertEqual(response.status_code, 403)
#
#         self.client.logout()
