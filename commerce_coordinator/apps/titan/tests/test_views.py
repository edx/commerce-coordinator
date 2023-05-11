"""
Tests for the titan app views.
"""
import logging
from unittest.mock import MagicMock

from django.test import TestCase
from django.urls import reverse
from mock import patch
from rest_framework.test import APIClient

from commerce_coordinator.apps.core.models import User
from commerce_coordinator.apps.core.signal_helpers import format_signal_results
from commerce_coordinator.apps.titan.tests.constants import (
    EXAMPLE_FULFILLMENT_REQUEST_PAYLOAD,
    EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD
)

logger = logging.getLogger(__name__)


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


@patch('commerce_coordinator.apps.titan.views.fulfill_order_placed_signal.send_robust',
       new_callable=FulfillOrderPlacedSignalMock)
class OrderFulfillViewTests(TestCase):
    """
    Tests for the OrderFulfillView.
    """
    # Disable unused-argument due to global @patch
    # pylint: disable=unused-argument

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

    def test_view_rejects_anonymous(self, mock_signal):
        """Check anonymous user requesting fulfillment receives a HTTP 401 Unauthorized."""

        # Send request without logging in.
        response = self.client.post(reverse('titan:order_fulfill'), EXAMPLE_FULFILLMENT_REQUEST_PAYLOAD, format='json')

        # Check 302 Found with redirect to login page.
        self.assertEqual(response.status_code, 401)

    def test_view_rejects_unauthorized(self, mock_signal):
        """Check unauthorized account requesting fulfillment receives a HTTP 403 Forbidden"""

        # Login as unprivileged user who should be forbidden on this endpoint.
        self.client.login(username=self.test_user_username, password=self.test_password)

        # Perform request as unprivileged user.
        response = self.client.post(reverse('titan:order_fulfill'), EXAMPLE_FULFILLMENT_REQUEST_PAYLOAD, format='json')

        # Check 403 Forbidden.
        self.assertEqual(response.status_code, 403)

    def test_view_returns_ok(self, mock_signal):
        """Check authorized user requesting fulfillment receives a HTTP 200 OK."""

        # Login
        self.client.login(username=self.test_staff_username, password=self.test_password)

        # Send request
        response = self.client.post(reverse('titan:order_fulfill'), EXAMPLE_FULFILLMENT_REQUEST_PAYLOAD, format='json')

        # Check 200 OK
        self.assertEqual(response.status_code, 200)

    def test_view_sends_expected_signal_parameters(self, mock_signal):
        """Check view sends expected signal parameters."""
        # Login
        self.client.login(username=self.test_staff_username, password=self.test_password)

        # Send request
        self.client.post(reverse('titan:order_fulfill'), EXAMPLE_FULFILLMENT_REQUEST_PAYLOAD, format='json')

        # Check expected response
        mock_signal.assert_called_once_with(**EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD)

    def test_view_returns_expected_response(self, mock_signal):
        """Check authorized account requesting fulfillment receives an expected response."""

        # Login
        self.client.login(username=self.test_staff_username, password=self.test_password)

        # Send request
        response = self.client.post(reverse('titan:order_fulfill'), EXAMPLE_FULFILLMENT_REQUEST_PAYLOAD, format='json')

        # Check expected response
        expected_response = format_signal_results(FulfillOrderPlacedSignalMock.return_value)
        self.assertEqual(response.json(), expected_response)

    def test_view_returns_expected_error(self, mock_signal):
        """Check authorized account requesting fulfillment with bad inputs receive an expected error."""

        # Login
        self.client.login(username=self.test_staff_username, password=self.test_password)

        # Add errors to example request
        payload_with_errors = EXAMPLE_FULFILLMENT_REQUEST_PAYLOAD.copy()
        payload_with_errors.pop('course_id')
        payload_with_errors['order_placed'] = 'bad_date'

        # Send request
        response = self.client.post(reverse('titan:order_fulfill'), payload_with_errors, format='json')

        # Check expected response
        expected_response = {
            'course_id': ['This field may not be null.'],
            'date_placed': ['A valid number is required.'],
        }
        self.assertEqual(response.json(), expected_response)
