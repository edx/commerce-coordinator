"""
Tests for the frontend_app_ecommerce app filters.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from commerce_coordinator.apps.frontend_app_ecommerce.filters import OrderHistoryRequested
from commerce_coordinator.apps.frontend_app_ecommerce.tests import (
    ECOMMERCE_REQUEST_EXPECTED_RESPONSE,
    ORDER_HISTORY_GET_PARAMETERS,
    CTOrdersForCustomerMock,
    EcommerceClientMock
)

User = get_user_model()


@patch('commerce_coordinator.apps.ecommerce.clients.EcommerceAPIClient.get_orders',
       new_callable=EcommerceClientMock)
@patch(
    'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_orders_for_customer',
    new_callable=CTOrdersForCustomerMock
)
class TestFrontendAppEcommerceFilters(TestCase):
    """
    Test class to verify standard behavior of the frontend_app_ecommerce filters.
    """

    # Disable unused-argument due to global @patch

    def test_order_history_requested_filter(self, _mock_ctorders, _mock_ecommerce_client):
        """
        Confirm that OrderHistoryRequested filter calls expected PipelineStep: GetEcommerceOrders
        """

        request = RequestFactory()
        request.user = User.objects.create_user(
            username='test', email='test@example.com', password='secret'
        )
        response = OrderHistoryRequested.run_filter(request, ORDER_HISTORY_GET_PARAMETERS)
        self.assertEqual(response[0], ECOMMERCE_REQUEST_EXPECTED_RESPONSE)
