"""Tests for the commercetools views"""

from unittest.mock import MagicMock, patch

import ddt
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from edx_django_utils.cache import TieredCache
from rest_framework.test import APIClient, APITestCase

from commerce_coordinator.apps.commercetools.tests.conftest import gen_customer, gen_order
from commerce_coordinator.apps.commercetools.tests.constants import (
    EXAMPLE_COMMERCETOOLS_ORDER_FULFILL_MESSAGE,
    EXAMPLE_COMMERCETOOLS_ORDER_SANCTIONED_MESSAGE,
    EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD
)
from commerce_coordinator.apps.commercetools.views import SingleInvocationAPIView
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


def get_order_with_bad_state_key():
    """Modify a canned order to have a bad transition/workflow state key"""
    order = gen_order(EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD['order_number'])
    order.state.obj.key = "XXXXXXX"
    return order


def get_order_with_missing_state():
    """Modify a canned order to have a bad transition/workflow state key"""
    order = gen_order(EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD['order_number'])
    order.state = None
    return order


class CTOrderBadStateKeyByIdMock(MagicMock):
    """
    A mock get_order_by_id call that always returns with a bad state
    """
    return_value = get_order_with_bad_state_key()


class CTOrderMissingStateByIdMock(MagicMock):
    """
    A mock get_order_by_id call that always returns with a missing state
    """
    return_value = get_order_with_missing_state()


class CTCustomerByIdMock(MagicMock):
    """
    A mock get_customer_by_id call that always returns
    EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD in the shape of format_signal_results.
    """
    return_value = gen_customer("hiya@text.example", "jim_34")


class TestSingleInvocationAPIView(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.view = SingleInvocationAPIView()

    def test_mark_running(self):
        view = "test_view"
        identifier = "test_identifier"

        # Test marking as running
        SingleInvocationAPIView._mark_running(view, identifier)
        self.assertTrue(SingleInvocationAPIView._is_running(view, identifier))

        # Test marking as not running
        SingleInvocationAPIView._mark_running(view, identifier, False)
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
        SingleInvocationAPIView._mark_running(view, identifier)

        # Call finalize_response
        self.view.finalize_response(request, response)

        # Check if marked as not running
        self.assertFalse(SingleInvocationAPIView._is_running(view, identifier))

    def test_handle_exception(self):
        view = "test_view"
        identifier = "test_identifier"

        # Set up request object
        request = self.client.get("/test-url/")
        self.view.meta_view = view
        self.view.meta_id = identifier

        # Mark as running
        SingleInvocationAPIView._mark_running(view, identifier)

        with self.assertRaises(Exception) as _:
            # Call handle_exception
            self.view.handle_exception(Exception())

            # Check if marked as not running
            self.assertFalse(SingleInvocationAPIView._is_running(view, identifier))


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
        User.objects.create_user(username=self.test_staff_username, password=self.test_password, is_staff=True)

    def tearDown(self):
        """Log out any user from client after test ends."""

        super().tearDown()
        TieredCache.dangerous_clear_all_tiers()
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

    def test_view_returns_expected_error_no_order(self, mock_customer, mock_order, mock_signal):
        """Check an authorized account requesting fulfillment unable to get customer to receive an expected error."""
        mock_customer.return_value = None
        # Login
        self.client.login(username=self.test_staff_username, password=self.test_password)

        # Send request
        response = self.client.post(self.url, data=EXAMPLE_COMMERCETOOLS_ORDER_FULFILL_MESSAGE, format='json')

        self.assertEqual(response.status_code, 200)

    def test_unauthorized_user(self, mock_customer, mock_order, mock_signal):
        """Check unauthorized user is forbidden."""

        # Login
        self.client.login(username=self.test_user_username, password=self.test_password)

        # Send request
        response = self.client.post(self.url, data=EXAMPLE_COMMERCETOOLS_ORDER_FULFILL_MESSAGE, format='json')

        # Check 403 Forbidden
        self.assertEqual(response.status_code, 403)


@ddt.ddt
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
    def test_view_returns_ok(self, mock_customer, mock_order):
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

    @patch(
        'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_order_by_id',
        new_callable=CTOrderByIdMock
    )
    @patch(
        'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_customer_by_id',
        new_callable=CTCustomerByIdMock
    )
    def test_view_returns_expected_error_no_order(self, mock_customer, mock_order):
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
    def test_view_returns_ok_bad_order_state(self, mock_customer, mock_order):
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
    def test_view_returns_ok_missing_order_state(self, mock_customer, mock_order):
        """Check authorized with missing order user requesting sanction receives a HTTP 200 OK."""

        # Login
        self.client.login(username=self.test_staff_username, password=self.test_password)

        # Send request
        response = self.client.post(self.url, data=EXAMPLE_COMMERCETOOLS_ORDER_SANCTIONED_MESSAGE, format='json')

        # Check 200 OK
        self.assertEqual(response.status_code, 200)


@ddt.ddt
class OrderReturnedViewTests(APITestCase):
    # Disable unused-argument due to global @patch
    # pylint: disable=unused-argument
    "Tests for order sanctioned view"
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
    def test_view_returns_ok(self, mock_customer, mock_order):
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

    @patch(
        'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_order_by_id',
        new_callable=CTOrderByIdMock
    )
    @patch(
        'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_customer_by_id',
        new_callable=CTCustomerByIdMock
    )
    def test_view_returns_expected_error_no_order(self, mock_customer, mock_order):
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
    def test_view_returns_ok_bad_order_state(self, mock_customer, mock_order):
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
    def test_view_returns_ok_missing_order_state(self, mock_customer, mock_order):
        """Check authorized with missing order user requesting sanction receives a HTTP 200 OK."""

        # Login
        self.client.login(username=self.test_staff_username, password=self.test_password)

        # Send request
        response = self.client.post(self.url, data=EXAMPLE_COMMERCETOOLS_ORDER_SANCTIONED_MESSAGE, format='json')

        # Check 200 OK
        self.assertEqual(response.status_code, 200)

    def test_unauthorized_user(self):
        """Check unauthorized user is forbidden."""

        # Login
        self.client.login(username=self.test_user_username, password=self.test_password)

        # Send request
        response = self.client.post(self.url, data=EXAMPLE_COMMERCETOOLS_ORDER_SANCTIONED_MESSAGE, format='json')

        # Check 403 Forbidden
        self.assertEqual(response.status_code, 403)
