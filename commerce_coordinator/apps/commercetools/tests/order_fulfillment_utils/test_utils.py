"""
Tests for order fulfillment utils
"""

import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from commerce_coordinator.apps.commercetools.order_fulfillment_utils.utils import (
    get_ct_order_and_customer,
    prepare_default_params
)


class TestGetCtOrderAndCustomer(unittest.TestCase):
    """Tests for get_ct_order_and_customer function."""

    @patch('commerce_coordinator.apps.commercetools.order_fulfillment_utils.utils.CommercetoolsAPIClient')
    def test_successful_retrieval(self, mock_client_class):
        """Test successful retrieval of order and customer."""

        mock_client = mock_client_class.return_value
        mock_order = Mock()
        mock_order.customer_id = "testcustomer"
        mock_order.id = "testorder"
        mock_customer = Mock()

        mock_client.get_order_by_id.return_value = mock_order
        mock_client.get_customer_by_id.return_value = mock_customer

        order, customer = get_ct_order_and_customer("test", "testorder", "message_id")

        mock_client.get_order_by_id.assert_called_once_with("testorder")
        mock_client.get_customer_by_id.assert_called_once_with("testcustomer")
        self.assertEqual(order, mock_order)
        self.assertEqual(customer, mock_customer)

    @patch('commerce_coordinator.apps.commercetools.order_fulfillment_utils.utils.CommercetoolsAPIClient')
    def test_order_not_found(self, mock_client_class):
        """Test exception handling when order is not found."""

        mock_client = mock_client_class.return_value
        mock_client.get_order_by_id.side_effect = Exception("Order not found")

        with self.assertRaises(Exception):
            get_ct_order_and_customer("test", "invalid_order", "message_id")

        mock_client.get_order_by_id.assert_called_once_with("invalid_order")
        mock_client.get_customer_by_id.assert_not_called()

    @patch('commerce_coordinator.apps.commercetools.order_fulfillment_utils.utils.CommercetoolsAPIClient')
    def test_customer_not_found(self, mock_client_class):
        """Test exception handling when customer is not found."""

        mock_client = mock_client_class.return_value
        mock_order = Mock()
        mock_order.customer_id = "testcustomer"
        mock_order.id = "testorder"

        mock_client.get_order_by_id.return_value = mock_order
        mock_client.get_customer_by_id.side_effect = Exception("Customer not found")

        with self.assertRaises(Exception):
            get_ct_order_and_customer("test", "testorder", "message_id")

        mock_client.get_order_by_id.assert_called_once_with("testorder")
        mock_client.get_customer_by_id.assert_called_once_with("testcustomer")


class TestPrepareDefaultParams(unittest.TestCase):
    """Tests for prepare_default_params function."""

    def test_prepare_default_params(self):
        """Test that default parameters are correctly prepared."""

        mock_order = Mock()
        mock_order.order_number = "ORD-12345"
        mock_order.id = "testorder"
        mock_order.last_modified_at = datetime(2025, 4, 28, 10, 30, 0, tzinfo=timezone.utc)

        params = prepare_default_params(mock_order, "testuser", "commercetools")

        expected_params = {
            'email_opt_in': True,
            'order_number': "ORD-12345",
            'order_id': "testorder",
            'provider_id': None,
            'edx_lms_user_id': "testuser",
            'date_placed': "2025-04-28T10:30:00Z",
            'source_system': "commercetools",
        }

        self.assertEqual(params, expected_params)
