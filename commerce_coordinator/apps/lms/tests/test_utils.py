"""
Tests for lms utils
"""
import unittest
from unittest.mock import Mock, patch

from commerce_coordinator.apps.lms.constants import CT_ABSOLUTE_DISCOUNT_TYPE, DEFAULT_BUNDLE_DISCOUNT_KEY
from commerce_coordinator.apps.lms.utils import (
    extract_uuids_from_predicate,
    get_order_line_item_info_from_entitlement_uuid,
    get_program_offer
)


class TestGetLineItemFromEntitlement(unittest.TestCase):
    """
    Tests for get_line_item_from_entitlement function
    """

    def get_mock_order_data(self, mock_line_items):
        """
        Create a mock order object with the given line items.
        """
        mock_order = Mock()
        mock_order.id = 'order123'
        mock_order.line_items = mock_line_items
        return mock_order

    def get_mock_line_item_data(self, return_value):
        """
        Create a mock line item object with the given return value for the custom field.
        """
        mock_line_item = Mock()
        mock_line_item.id = 'line_item123'
        mock_line_item.custom.fields.get.return_value = return_value

        return mock_line_item

    @patch('commerce_coordinator.apps.lms.utils.CommercetoolsAPIClient')
    def test_get_line_item_from_entitlement_success(self, MockCommercetoolsAPIClient):
        mock_ct_api_client = MockCommercetoolsAPIClient.return_value
        mock_line_item = self.get_mock_line_item_data('entitlement123')
        mock_order = self.get_mock_order_data([mock_line_item])
        mock_ct_api_client.get_order_by_number.return_value = mock_order

        order_id, line_item_id = get_order_line_item_info_from_entitlement_uuid('order123', 'entitlement123')

        self.assertEqual(order_id, 'order123')
        self.assertEqual(line_item_id, 'line_item123')

    @patch('commerce_coordinator.apps.lms.utils.CommercetoolsAPIClient')
    def test_get_line_item_from_entitlement_no_matching_entitlement(self, MockCommercetoolsAPIClient):
        mock_ct_api_client = MockCommercetoolsAPIClient.return_value
        mock_line_item = self.get_mock_line_item_data('different_entitlement')
        mock_order = self.get_mock_order_data([mock_line_item])
        mock_ct_api_client.get_order_by_number.return_value = mock_order

        order_id, line_item_id = get_order_line_item_info_from_entitlement_uuid('order123', 'entitlement123')

        self.assertEqual(order_id, 'order123')
        self.assertEqual(line_item_id, '')

    @patch('commerce_coordinator.apps.lms.utils.CommercetoolsAPIClient')
    def test_get_line_item_from_entitlement_no_line_items(self, MockCommercetoolsAPIClient):
        mock_ct_api_client = MockCommercetoolsAPIClient.return_value
        mock_order = self.get_mock_order_data([])
        mock_ct_api_client.get_order_by_number.return_value = mock_order

        order_id, line_item_id = get_order_line_item_info_from_entitlement_uuid('order123', 'entitlement123')

        self.assertEqual(order_id, 'order123')
        self.assertEqual(line_item_id, '')


class TestGetProgramOffer(unittest.TestCase):
    """
    Tests for get_program_offer util function
    """
    def setUp(self):
        self.cart_discounts = [
            {
                "key": "BUNDLE_15_OFF",
                "target": {"predicate": 'custom.bundleId is defined and (custom.bundleId = "bundle-key-123")'},
                "value": {"type": "absolute", "money": [{"centAmount": 1500}]}
            },
            {
                "key": DEFAULT_BUNDLE_DISCOUNT_KEY,
                "target": {"predicate": 'custom.bundleId is defined and (custom.bundleId != "bundle-key-123")'},
                "value": {"type": "relative", "permyriad": 1000}
            }
        ]

    def test_extract_uuids_from_predicate(self):
        predicate = 'custom.bundleId = "12345" and custom.bundleId = "67890"'
        result = extract_uuids_from_predicate(predicate)
        self.assertEqual(result, ["12345", "67890"])

    def test_get_program_offer_with_specific_bundle(self):
        bundle_key = "bundle-key-123"
        expected_result = {
            "discount_value_in_cents": 1500,
            "discount_type": "absolute",
            "key": "BUNDLE_15_OFF"
        }
        self.assertEqual(get_program_offer(self.cart_discounts, bundle_key), expected_result)

    def test_get_program_offer_with_default_discount(self):
        bundle_key = "non-existent-bundle"
        expected_result = {
            "discount_value_in_cents": 1000,
            "discount_type": "relative",
            "key": DEFAULT_BUNDLE_DISCOUNT_KEY
        }
        self.assertEqual(get_program_offer(self.cart_discounts, bundle_key), expected_result)

    def test_get_program_offer_with_no_matching_discount(self):
        bundle_key = "unknown-bundle"
        self.assertIsNone(get_program_offer([], bundle_key))

    def test_get_program_offer_excluded_from_default_discount(self):
        cart_discounts = [
            {
                "key": DEFAULT_BUNDLE_DISCOUNT_KEY,
                "target": {"predicate": 'custom.bundleId != "bundle_3"'},
                "value": {"type": CT_ABSOLUTE_DISCOUNT_TYPE, "money": [{"centAmount": 1000}]}
            }
        ]
        bundle_key = "bundle_3"
        result = get_program_offer(cart_discounts, bundle_key)
        self.assertIsNone(result)
