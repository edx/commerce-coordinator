"""
Tests for the ecommerce app API clients.
"""
import logging

from django.test import TestCase
from mock import patch

from commerce_coordinator.apps.ecommerce.clients import EcommerceAPIClient
from commerce_coordinator.apps.frontend_app_ecommerce.tests import (
    ECOMMERCE_REQUEST_EXPECTED_RESPONSE,
    ORDER_HISTORY_GET_PARAMETERS
)

logger = logging.getLogger(__name__)


class EcommerceClientTests(TestCase):
    """
    Verify endpoint availability for order retrieval endpoint(s)
    """

    @patch('commerce_coordinator.apps.ecommerce.clients.EcommerceAPIClient.get_orders')
    def test_ecommerce_api_client(self, mock_response):
        """We can call the EcommerceAPIClient successfully."""
        mock_response.return_value = ECOMMERCE_REQUEST_EXPECTED_RESPONSE

        ecommerce_api_client = EcommerceAPIClient()
        ecommerce_response = ecommerce_api_client.get_orders(ORDER_HISTORY_GET_PARAMETERS)
        self.assertEqual(ECOMMERCE_REQUEST_EXPECTED_RESPONSE, ecommerce_response)
