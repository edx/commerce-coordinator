"""
Tests for the frontend_app_ecommerce app filters.
"""

from django.test import TestCase
from mock import patch

from commerce_coordinator.apps.frontend_app_ecommerce.filters import OrderHistoryRequested
from commerce_coordinator.apps.frontend_app_ecommerce.tests import (
    ECOMMERCE_REQUEST_EXPECTED_RESPONSE,
    ORDER_HISTORY_GET_PARAMETERS
)
from commerce_coordinator.apps.frontend_app_ecommerce.tests.test_views import EcommerceClientMock


@patch('commerce_coordinator.apps.ecommerce.clients.EcommerceApiClient.get_orders',
       new_callable=EcommerceClientMock)
class TestFrontendAppEcommerceFilters(TestCase):
    """
    Test class to verify standard behavior of the frontend_app_ecommerce filters.
    """
    # Disable unused-argument due to global @patch
    # pylint: disable=unused-argument

    def test_order_history_requested_filter(self, mock_ecommerce_client):
        """
        Confirm that OrderHistoryRequested filter calls expected PipelineStep: GetEcommerceOrders
        """

        response = OrderHistoryRequested.run_filter(ORDER_HISTORY_GET_PARAMETERS)
        self.assertEqual(response, ECOMMERCE_REQUEST_EXPECTED_RESPONSE)
