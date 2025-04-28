"""
Tests for order fulfillment views.
"""
import json
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from commerce_coordinator.apps.lms.clients import FulfillmentType


class TestFulfillmentResponseWebhookView(TestCase):
    """
    Tests for FulfillmentResponseWebhookView.
    """
    def setUp(self):
        """Set up data for the test cases."""
        super().setUp()
        self.client = APIClient()
        self.url = reverse('order_fulfillment:fulfillment_response_webhook')
        self.valid_payload = {
            'fulfillment_type': FulfillmentType.ENTITLEMENT.value,
            'entitlement_uuid': '12345678-1234-5678-1234-567812345678',
            'order_id': 'EDX-123456',
            'order_version': '1.0',
            'line_item_id': 'item-123',
            'item_quantity': 1,
            'line_item_state_id': 'state-123',
            'is_fulfilled': True
        }

    @patch('commerce_coordinator.apps.order_fulfillment.views.HMACSignatureWebhookAuthentication.authenticate')
    @patch('commerce_coordinator.apps.order_fulfillment.views.fulfillment_completed_update_ct_line_item_signal')
    def test_successful_fulfillment(self, mock_signal, mock_authenticate):
        """
        Test successful fulfillment webhook processing.
        """
        mock_authenticate.return_value = None

        response = self.client.post(
            self.url,
            data=json.dumps(self.valid_payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'message': 'Order Fulfillment Response event processed successfully.'})

        # Verify signal was called with correct parameters
        mock_signal.send_robust.assert_called_once()
        call_kwargs = mock_signal.send_robust.call_args[1]
        self.assertTrue(call_kwargs['is_fulfilled'])
        self.assertEqual(call_kwargs['entitlement_uuid'], self.valid_payload['entitlement_uuid'])
        self.assertEqual(call_kwargs['order_id'], self.valid_payload['order_id'])

    @patch('commerce_coordinator.apps.order_fulfillment.views.HMACSignatureWebhookAuthentication.authenticate')
    def test_missing_required_fields(self, mock_authenticate):
        """
        Test webhook validation with missing required fields.
        """
        mock_authenticate.return_value = None

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

    @patch('commerce_coordinator.apps.order_fulfillment.views.HMACSignatureWebhookAuthentication.authenticate')
    def test_entitlement_uuid_missing_for_entitlement_fulfillment(self, mock_authenticate):
        """
        Test validation error when entitlement UUID is missing for entitlement fulfillment.
        """
        mock_authenticate.return_value = None

        payload = self.valid_payload.copy()
        del payload['entitlement_uuid']

        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        print('\n\n\n\n response', response.json())
        self.assertIn('Entitlement uuid is required for Entitlement Fulfillment.', response.json())

    @patch('commerce_coordinator.apps.order_fulfillment.views.HMACSignatureWebhookAuthentication.authenticate')
    @patch('commerce_coordinator.apps.order_fulfillment.views.fulfillment_completed_update_ct_line_item_signal')
    def test_fulfillment_without_entitlement(self, mock_signal, mock_authenticate):
        """
        Test fulfillment webhook without entitlement UUID for non-entitlement fulfillment types.
        """
        mock_authenticate.return_value = None

        payload = self.valid_payload.copy()
        payload['fulfillment_type'] = 'OTHER_TYPE'
        del payload['entitlement_uuid']

        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_signal.send_robust.assert_called_once()

    @patch('commerce_coordinator.apps.order_fulfillment.views.HMACSignatureWebhookAuthentication.authenticate')
    def test_method_not_allowed(self, mock_authenticate):
        """
        Test that only POST method is allowed.
        """
        mock_authenticate.return_value = None

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    @patch('commerce_coordinator.apps.order_fulfillment.views.HMACSignatureWebhookAuthentication.authenticate')
    @patch('commerce_coordinator.apps.order_fulfillment.serializers.FulfillOrderWebhookSerializer.is_valid')
    def test_serializer_validation_error(self, mock_is_valid, mock_authenticate):
        """
        Test handling of serializer validation errors.
        """
        mock_authenticate.return_value = None

        mock_is_valid.side_effect = ValidationError('Invalid data')

        response = self.client.post(
            self.url,
            data=json.dumps(self.valid_payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Invalid data', response.json())
