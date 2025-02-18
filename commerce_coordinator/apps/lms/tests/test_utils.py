"""
Tests for lms utils
"""
import unittest
from unittest.mock import Mock, patch

from commerce_coordinator.apps.lms.utils import get_line_item_from_entitlement


class TestGetLineItemFromEntitlement(unittest.TestCase):
    """
    Tests for get_line_item_from_entitlement function
    """

    @patch('commerce_coordinator.apps.lms.utils.CommercetoolsAPIClient')
    def test_get_line_item_from_entitlement_success(self, MockCommercetoolsAPIClient):
        mock_ct_api_client = MockCommercetoolsAPIClient.return_value
        mock_order = Mock()
        mock_order.id = 'order123'
        mock_line_item = Mock()
        mock_line_item.id = 'line_item123'
        mock_line_item.custom.fields.get.return_value = 'entitlement123'
        mock_order.line_items = [mock_line_item]
        mock_ct_api_client.get_order_by_number.return_value = mock_order

        order_id, line_item_id = get_line_item_from_entitlement('order123', 'entitlement123')

        self.assertEqual(order_id, 'order123')
        self.assertEqual(line_item_id, 'line_item123')

    @patch('commerce_coordinator.apps.lms.utils.CommercetoolsAPIClient')
    def test_get_line_item_from_entitlement_no_matching_entitlement(self, MockCommercetoolsAPIClient):
        mock_ct_api_client = MockCommercetoolsAPIClient.return_value
        mock_order = Mock()
        mock_order.id = 'order123'
        mock_line_item = Mock()
        mock_line_item.id = 'line_item123'
        mock_line_item.custom.fields.get.return_value = 'different_entitlement'
        mock_order.line_items = [mock_line_item]
        mock_ct_api_client.get_order_by_number.return_value = mock_order

        order_id, line_item_id = get_line_item_from_entitlement('order123', 'entitlement123')

        self.assertEqual(order_id, 'order123')
        self.assertEqual(line_item_id, '')

    @patch('commerce_coordinator.apps.lms.utils.CommercetoolsAPIClient')
    def test_get_line_item_from_entitlement_no_line_items(self, MockCommercetoolsAPIClient):
        mock_ct_api_client = MockCommercetoolsAPIClient.return_value
        mock_order = Mock()
        mock_order.id = 'order123'
        mock_order.line_items = []
        mock_ct_api_client.get_order_by_number.return_value = mock_order

        order_id, line_item_id = get_line_item_from_entitlement('order123', 'entitlement123')

        self.assertEqual(order_id, 'order123')
        self.assertEqual(line_item_id, '')
