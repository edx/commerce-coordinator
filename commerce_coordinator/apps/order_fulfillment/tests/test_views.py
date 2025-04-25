"""
Tests for order fulfillment views.
"""
import json
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from commerce_coordinator.apps.lms.clients import FulfillmentType


class TestFulfillOrderWebhookView(TestCase):
    """
    Tests for FulfillOrderWebhookView.
    """
    def setUp(self):
        """Set up data for the test cases."""
        super().setUp()
        self.client = APIClient()
        self.url = reverse('order_fulfillment:fulfill_order_webhook')
        self.valid_payload = {
            'fulfillment_type': FulfillmentType.ENTITLEMENT.value,
            'entitlement_uuid': '12345678-1234-5678-1234-567812345678',
            'order_id': 'EDX-123456',
            'order_version': '1.0',
            'line_item_id': 'item-123',
            'item_quantity': 1,
            'line_item_state_id': 'state-123'
        }

    @patch('commerce_coordinator.apps.order_fulfillment.views.fulfillment_completed_update_ct_line_item_signal')
    def test_successful_fulfillment(self, mock_signal):
        """
        Test successful fulfillment webhook processing.
        """
        response = self.client.post(
            self.url,
            data=json.dumps(self.valid_payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'message': 'Fulfillment event processed successfully'})

        # Verify signal was called with correct parameters
        mock_signal.send_robust.assert_called_once()
        call_kwargs = mock_signal.send_robust.call_args[1]
        self.assertTrue(call_kwargs['is_fulfilled'])
        self.assertEqual(call_kwargs['entitlement_uuid'], self.valid_payload['entitlement_uuid'])
        self.assertEqual(call_kwargs['order_id'], self.valid_payload['order_id'])

    def test_missing_required_fields(self):
        """
        Test webhook validation with missing required fields.
        """
        invalid_payload = {
            'fulfillment_type': FulfillmentType.ENTITLEMENT.value,
            'entitlement_uuid': '12345678-1234-5678-1234-567812345678'
            # Missing other required fields
        }

        response = self.client.post(
            self.url,
            data=json.dumps(invalid_payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('commerce_coordinator.apps.order_fulfillment.views.fulfillment_completed_update_ct_line_item_signal')
    def test_fulfillment_without_entitlement(self, mock_signal):
        """
        Test fulfillment webhook without entitlement UUID.
        """
        payload = self.valid_payload.copy()
        del payload['entitlement_uuid']

        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_signal.send_robust.assert_called_once()

    def test_method_not_allowed(self):
        """
        Test that only POST method is allowed.
        """
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
