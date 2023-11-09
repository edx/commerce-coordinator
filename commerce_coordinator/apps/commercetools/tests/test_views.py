""" Commercetools Order History testcases """
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from commerce_coordinator.apps.commercetools.clients import PaginatedResult
from commerce_coordinator.apps.commercetools.tests.conftest import gen_order
from commerce_coordinator.apps.commercetools.tests.test_data import gen_customer
from commerce_coordinator.apps.core.tests.utils import uuid4_str
from commerce_coordinator.apps.frontend_app_ecommerce.tests.test_views import EcommerceClientMock

User = get_user_model()

orders = [gen_order(uuid4_str())]


class CTOrdersForCustomerMock(MagicMock):
    """A mock EcommerceAPIClient that always returns ECOMMERCE_REQUEST_EXPECTED_RESPONSE."""
    return_value = (
        PaginatedResult(orders, len(orders), 0),
        gen_customer(email='test@example.com', un="test")
    )


class OrderHistoryViewTests(APITestCase):
    """
    Tests for order history view
    """

    # Define test user properties
    test_user_username = 'test'
    test_user_email = 'test@example.com'
    test_user_password = 'secret'
    url = reverse('commercetools:order_history')

    def setUp(self):
        """Create test user before test starts."""
        super().setUp()
        self.user = User.objects.create_user(
            self.test_user_username,
            self.test_user_email,
            self.test_user_password,
            lms_user_id=127,
            # TODO: Remove is_staff=True
            is_staff=True,
        )

    def tearDown(self):
        """Log out any user from the client after test ends."""
        super().tearDown()
        self.client.logout()

    @patch(
        'commerce_coordinator.apps.ecommerce.clients.EcommerceAPIClient.get_orders',
        new_callable=EcommerceClientMock
    )
    @patch(
        'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_orders_for_customer',
        new_callable=CTOrdersForCustomerMock
    )
    def test_order_history_functional(self, _, __):
        """Happy path test function for CT Order History"""
        self.client.force_authenticate(user=self.user)
        query_params = {}  # we don't accept any rn

        response = self.client.get(self.url, data=query_params)
        self.assertEqual(response.status_code, 200)

        response_json: dict = response.json()

        self.assertIn('order_data', response_json.keys())
        self.assertEqual(2, len(response_json['order_data']))
        # because of how the dates work within this test the old system value should be second as its date is older
        self.assertEqual(response_json['order_data'][1]['payment_processor'], 'cybersource-rest')

    def test_order_history_denied(self):
        """bad/incomplete auth test function for CT Order History"""

        self.client.force_authenticate(user=User.objects.create_user(
                "joey",
                "something@something.com",
                "shh its @ secret!",
                # TODO: Remove is_staff=True
                is_staff=True,
            ))
        query_params = {}  # we don't accept any rn

        response = self.client.get(self.url, data=query_params)
        self.assertEqual(response.status_code, 403)

        self.client.logout()
