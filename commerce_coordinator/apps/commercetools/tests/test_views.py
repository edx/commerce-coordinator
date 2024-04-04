"""Tests for the commercetools views"""

# pylint: disable=protected-access

from unittest.mock import patch

import ddt
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from edx_django_utils.cache import TieredCache
from rest_framework.test import APIClient, APITestCase

from commerce_coordinator.apps.commercetools.tests.constants import (
    EXAMPLE_COMMERCETOOLS_ORDER_FULFILL_MESSAGE,
    EXAMPLE_COMMERCETOOLS_ORDER_SANCTIONED_MESSAGE
)
from commerce_coordinator.apps.commercetools.tests.mocks import (
    CTCustomerByIdMock,
    CTOrderBadStateKeyByIdMock,
    CTOrderByIdMock,
    CTOrderMissingStateByIdMock,
    SendRobustSignalMock
)
from commerce_coordinator.apps.commercetools.views import SingleInvocationAPIView
from commerce_coordinator.apps.core.models import User


class TestSingleInvocationAPIView(TestCase):
    """Tests for SingleInvocationAPIView"""

    def setUp(self):
        self.client = APIClient()
        self.view = SingleInvocationAPIView()

    def test_mark_running(self):
        view = "test_view"
        identifier = "test_identifier"

        # Test marking as running
        self.view.mark_running(view, identifier)
        self.assertTrue(SingleInvocationAPIView._is_running(view, identifier))

        # Test marking as not running
        self.view.mark_running(view, identifier, False)
        self.assertFalse(SingleInvocationAPIView._is_running(view, identifier))

    def test_finalize_response(self):
        view = "test_view"
        identifier = "test_identifier"

        # Set up request and response objects
        request = self.client.get("/test-url/")
        self.view.meta_view = view
        self.view.meta_id = identifier
        response = HttpResponse(status=200)
        self.view.headers = response.headers

        # Mark as running
        self.view.mark_running(view, identifier)

        # Call finalize_response
        self.view.finalize_response(request, response)

        # Check if marked as not running
        self.assertTrue(SingleInvocationAPIView._is_running(view, identifier))

    def test_handle_exception(self):
        view = "test_view"
        identifier = "test_identifier"

        # Set up request object
        request = self.client.get("/test-url/")
        self.view.meta_view = view
        self.view.meta_id = identifier

        # Mark as running
        self.view.mark_running(view, identifier)

        with self.assertRaises(Exception) as _:
            # Call handle_exception
            self.view.handle_exception(Exception())

            # Check if marked as not running
            self.assertFalse(SingleInvocationAPIView._is_running(view, identifier))


@ddt.ddt
@patch('commerce_coordinator.apps.commercetools.sub_messages.signals_dispatch'
       '.fulfill_order_placed_message_signal.send_robust',
       new_callable=SendRobustSignalMock)
class OrderFulfillViewTests(APITestCase):
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
        User.objects.create_user(username=self.test_staff_username, password=self.test_password, is_staff=True)

    def tearDown(self):
        """Log out any user from client after test ends."""

        super().tearDown()
        TieredCache.dangerous_clear_all_tiers()
        self.client.logout()

    def test_view_returns_ok(self, _mock_signal):
        """Check authorized user requesting fulfillment receives a HTTP 200 OK."""

        # Login
        self.client.login(username=self.test_staff_username, password=self.test_password)

        # Send request
        response = self.client.post(self.url, data=EXAMPLE_COMMERCETOOLS_ORDER_FULFILL_MESSAGE, format='json')

        # Check 200 OK
        self.assertEqual(response.status_code, 200)

    # # TODO: GRM: Move to Signals tests
    # def test_view_sends_expected_signal_parameters(self, mock_customer, mock_order, mock_signal):
    #     """Check view sends expected signal parameters."""
    #     # Login
    #     self.client.login(username=self.test_staff_username, password=self.test_password)
    #
    #     # Send request
    #     self.client.post(self.url, data=EXAMPLE_COMMERCETOOLS_ORDER_FULFILL_MESSAGE, format='json')
    #
    #     # Check expected response
    #     mock_signal.assert_called_once_with(**EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD)

    # # TODO: GRM: Move to Signals tests
    # @patch("commerce_coordinator.apps.commercetools.views.send_order_confirmation_email")
    # def test_view_triggers_order_confirmation_email(self, mock_send_email, mock_customer, mock_order, mock_signal):
    #     """Check view sends expected signal parameters."""
    #     self.client.login(username=self.test_staff_username, password=self.test_password)
    #
    #     self.client.post(self.url, data=EXAMPLE_COMMERCETOOLS_ORDER_FULFILL_MESSAGE, format='json')
    #
    #     mock_send_email.assert_called_once()

    def test_view_returns_expected_error(self, _mock_signal):
        """Check an authorized account requesting fulfillment with bad inputs receive an expected error."""

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

    def test_view_returns_expected_error_no_order(self, _mock_signal):
        """Check an authorized account requesting fulfillment unable to get customer to receive an expected error."""

        # Login
        self.client.login(username=self.test_staff_username, password=self.test_password)

        # Send request
        response = self.client.post(self.url, data=EXAMPLE_COMMERCETOOLS_ORDER_FULFILL_MESSAGE, format='json')

        self.assertEqual(response.status_code, 200)

    def test_unauthorized_user(self, _mock_signal):
        """Check unauthorized user is forbidden."""

        # Login
        self.client.login(username=self.test_user_username, password=self.test_password)

        # Send request
        response = self.client.post(self.url, data=EXAMPLE_COMMERCETOOLS_ORDER_FULFILL_MESSAGE, format='json')

        # Check 403 Forbidden
        self.assertEqual(response.status_code, 403)


@ddt.ddt
@patch('commerce_coordinator.apps.commercetools.sub_messages.signals_dispatch'
       '.fulfill_order_sanctioned_message_signal.send_robust',
       new_callable=SendRobustSignalMock)
class OrderSanctionedViewTests(APITestCase):
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
        User.objects.create_user(username=self.test_staff_username, password=self.test_password, is_staff=True)

    def tearDown(self):
        """Log out any user from client after test ends."""

        super().tearDown()
        TieredCache.dangerous_clear_all_tiers()
        self.client.logout()

    @patch(
        'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_order_by_id',
        new_callable=CTOrderByIdMock
    )
    @patch(
        'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_customer_by_id',
        new_callable=CTCustomerByIdMock
    )
    def test_view_returns_ok(self, _mock_customer, _mock_order, _mock_signal):
        """Check authorized user requesting sanction receives a HTTP 200 OK."""

        # Login
        self.client.login(username=self.test_staff_username, password=self.test_password)

        # Send request
        response = self.client.post(self.url, data=EXAMPLE_COMMERCETOOLS_ORDER_SANCTIONED_MESSAGE, format='json')

        # Check 200 OK
        self.assertEqual(response.status_code, 200)

    @patch(
        'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_order_by_id',
        new_callable=CTOrderByIdMock
    )
    @patch(
        'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_customer_by_id',
        new_callable=CTCustomerByIdMock
    )
    def test_view_returns_expected_error(self, _mock_customer, _mock_order, _mock_signal):
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

    @patch(
        'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_order_by_id',
        new_callable=CTOrderByIdMock
    )
    @patch(
        'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_customer_by_id',
        new_callable=CTCustomerByIdMock
    )
    def test_view_returns_expected_error_no_order(self, mock_customer, _mock_order, _mock_signal):
        """Check authorized account requesting fulfillment unable to get customer receive an expected error."""
        mock_customer.return_value = None
        # Login
        self.client.login(username=self.test_staff_username, password=self.test_password)

        # Send request
        response = self.client.post(self.url, data=EXAMPLE_COMMERCETOOLS_ORDER_SANCTIONED_MESSAGE, format='json')

        self.assertEqual(response.status_code, 200)

    @patch(
        'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_order_by_id',
        new_callable=CTOrderBadStateKeyByIdMock
    )
    @patch(
        'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_customer_by_id',
        new_callable=CTCustomerByIdMock
    )
    def test_view_returns_ok_bad_order_state(self, _mock_customer, _mock_order, _mock_signal):
        """Check authorized user requesting sanction receives a HTTP 200 OK."""

        # Login
        self.client.login(username=self.test_staff_username, password=self.test_password)

        # Send request
        response = self.client.post(self.url, data=EXAMPLE_COMMERCETOOLS_ORDER_SANCTIONED_MESSAGE, format='json')

        # Check 200 OK
        self.assertEqual(response.status_code, 200)

    @patch(
        'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_order_by_id',
        new_callable=CTOrderMissingStateByIdMock
    )
    @patch(
        'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_customer_by_id',
        new_callable=CTCustomerByIdMock
    )
    def test_view_returns_ok_missing_order_state(self, _mock_customer, _mock_order, _mock_signal):
        """Check authorized with missing order user requesting sanction receives a HTTP 200 OK."""

        # Login
        self.client.login(username=self.test_staff_username, password=self.test_password)

        # Send request
        response = self.client.post(self.url, data=EXAMPLE_COMMERCETOOLS_ORDER_SANCTIONED_MESSAGE, format='json')

        # Check 200 OK
        self.assertEqual(response.status_code, 200)


@ddt.ddt
@patch('commerce_coordinator.apps.commercetools.sub_messages.signals_dispatch'
       '.fulfill_order_returned_signal.send_robust',
       new_callable=SendRobustSignalMock)
class OrderReturnedViewTests(APITestCase):
    """Tests for order sanctioned view"""
    url = reverse('commercetools:returned')

    # Use Django Rest Framework client for self.client
    client_class = APIClient

    test_user_username = 'test_user'
    test_staff_username = 'test_staff_user'
    test_password = 'test_password'

    def setUp(self):
        """Create test user before test starts."""

        super().setUp()

        User.objects.create_user(username=self.test_user_username, password=self.test_password)
        User.objects.create_user(username=self.test_staff_username, password=self.test_password, is_staff=True)

    def tearDown(self):
        """Log out any user from client after test ends."""

        super().tearDown()
        TieredCache.dangerous_clear_all_tiers()
        self.client.logout()

    @patch(
        'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_order_by_id',
        new_callable=CTOrderByIdMock
    )
    @patch(
        'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_customer_by_id',
        new_callable=CTCustomerByIdMock
    )
    def test_view_returns_ok(self, _mock_customer, _mock_order, _mock_signal):
        """Check authorized user requesting sanction receives a HTTP 200 OK."""

        # Login
        self.client.login(username=self.test_staff_username, password=self.test_password)

        # Send request
        response = self.client.post(self.url, data=EXAMPLE_COMMERCETOOLS_ORDER_SANCTIONED_MESSAGE, format='json')

        # Check 200 OK
        self.assertEqual(response.status_code, 200)

    @patch(
        'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_order_by_id',
        new_callable=CTOrderByIdMock
    )
    @patch(
        'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_customer_by_id',
        new_callable=CTCustomerByIdMock
    )
    def test_view_returns_expected_error(self, _mock_customer, _mock_order, _mock_signal):
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

    @patch(
        'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_order_by_id',
        new_callable=CTOrderByIdMock
    )
    @patch(
        'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_customer_by_id',
        new_callable=CTCustomerByIdMock
    )
    def test_view_returns_expected_error_no_order(self, mock_customer, _mock_order, _mock_signal):
        """Check authorized account requesting fulfillment unable to get customer receive an expected error."""
        mock_customer.return_value = None
        # Login
        self.client.login(username=self.test_staff_username, password=self.test_password)

        # Send request
        response = self.client.post(self.url, data=EXAMPLE_COMMERCETOOLS_ORDER_SANCTIONED_MESSAGE, format='json')

        self.assertEqual(response.status_code, 200)

    @patch(
        'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_order_by_id',
        new_callable=CTOrderBadStateKeyByIdMock
    )
    @patch(
        'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_customer_by_id',
        new_callable=CTCustomerByIdMock
    )
    def test_view_returns_ok_bad_order_state(self, _mock_customer, _mock_order, _mock_signal):
        """Check authorized user requesting sanction receives a HTTP 200 OK."""

        # Login
        self.client.login(username=self.test_staff_username, password=self.test_password)

        # Send request
        response = self.client.post(self.url, data=EXAMPLE_COMMERCETOOLS_ORDER_SANCTIONED_MESSAGE, format='json')

        # Check 200 OK
        self.assertEqual(response.status_code, 200)

    @patch(
        'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_order_by_id',
        new_callable=CTOrderMissingStateByIdMock
    )
    @patch(
        'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_customer_by_id',
        new_callable=CTCustomerByIdMock
    )
    def test_view_returns_ok_missing_order_state(self, _mock_customer, _mock_order, _mock_signal):
        """Check authorized with missing order user requesting sanction receives a HTTP 200 OK."""

        # Login
        self.client.login(username=self.test_staff_username, password=self.test_password)

        # Send request
        response = self.client.post(self.url, data=EXAMPLE_COMMERCETOOLS_ORDER_SANCTIONED_MESSAGE, format='json')

        # Check 200 OK
        self.assertEqual(response.status_code, 200)

    def test_unauthorized_user(self, _mock_signal):
        """Check unauthorized user is forbidden."""

        # Login
        self.client.login(username=self.test_user_username, password=self.test_password)

        # Send request
        response = self.client.post(self.url, data=EXAMPLE_COMMERCETOOLS_ORDER_SANCTIONED_MESSAGE, format='json')

        # Check 403 Forbidden
        self.assertEqual(response.status_code, 403)
