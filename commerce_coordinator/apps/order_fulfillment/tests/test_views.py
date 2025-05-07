from unittest.mock import patch

import ddt
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from commerce_coordinator.apps.commercetools.tests.mocks import SendRobustSignalMock
from commerce_coordinator.apps.core.models import User
from commerce_coordinator.apps.lms.clients import FulfillmentType

EXAMPLE_ORDER_FULFILLMENT_RESPONSE_API_PAYLOAD = {
    "detail": {
        "fulfillment_type": "ENTITLEMENT",
        "is_fulfilled": True,
        "entitlement_uuid": "123e4567-e89b-12d3-a456-426614174000",
        "order_id": "order-123",
        "order_version": "5",
        "line_item_id": "line-item-456",
        "item_quantity": 2,
        "line_item_state_id": "state-789"
    }
}


@ddt.ddt
@patch('commerce_coordinator.apps.order_fulfillment.views.fulfillment_completed_update_ct_line_item_signal.send_robust',
       new_callable=SendRobustSignalMock)
class FulfillmentResponseWebhookViewTests(APITestCase):
    """Tests for Fulfillment Response Webhook view."""
    url = reverse('order_fulfillment:fulfillment_response_webhook')

    client_class = APIClient
    test_user_username = 'test_user'
    test_staff_username = 'test_staff_user'
    test_password = 'test_password'

    def setUp(self):
        super().setUp()
        User.objects.create_user(username=self.test_user_username, password=self.test_password)
        User.objects.create_user(username=self.test_staff_username, password=self.test_password, is_staff=True)

    def tearDown(self):
        super().tearDown()
        self.client.logout()

    def test_fulfillment_webhook_success(self, mock_signal):
        """Test successful fulfillment webhook call by staff user."""
        self.client.login(username=self.test_staff_username, password=self.test_password)
        response = self.client.post(self.url, data=EXAMPLE_ORDER_FULFILLMENT_RESPONSE_API_PAYLOAD, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'message': 'Order Fulfillment Response event processed successfully.'})
        mock_signal.assert_called_once()

    def test_fulfillment_webhook_missing_entitlement_uuid(self, mock_signal):
        """Test entitlement fulfillment fails when `entitlement_uuid` is missing."""
        self.client.login(username=self.test_staff_username, password=self.test_password)
        data = EXAMPLE_ORDER_FULFILLMENT_RESPONSE_API_PAYLOAD.copy()
        data['detail']['fulfillment_type'] = FulfillmentType.ENTITLEMENT.value
        data['detail'].pop('entitlement_uuid', None)
        response = self.client.post(self.url, data=data, format='json')

        print('response = ', response.json())
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Entitlement uuid is required for Entitlement Fulfillment.', response.json())
        mock_signal.assert_not_called()

    def test_fulfillment_webhook_invalid_payload(self, mock_signal):
        """Test invalid payload raises validation error."""
        self.client.login(username=self.test_staff_username, password=self.test_password)
        response = self.client.post(self.url, data={'detail': {'payload': 'Invalid payload'}}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_signal.assert_not_called()

    def test_unauthorized_user_access(self, mock_signal):
        """Test a non-staff user is forbidden from accessing the webhook."""
        self.client.login(username=self.test_user_username, password=self.test_password)
        response = self.client.post(self.url, data=EXAMPLE_ORDER_FULFILLMENT_RESPONSE_API_PAYLOAD, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        mock_signal.assert_not_called()
