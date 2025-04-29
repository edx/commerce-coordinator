"""
Tests for the order fulfillment app API clients.
"""
from django.test import override_settings
from mock import patch

from commerce_coordinator.apps.core.clients import urljoin_directory
from commerce_coordinator.apps.core.tests.utils import CoordinatorOAuthClientTestCase
from commerce_coordinator.apps.lms.tests.constants import (
    EXAMPLE_FULFILLMENT_LOGGING_OBJ,
    EXAMPLE_FULFILLMENT_SERVICE_REDIRECTION_PAYLOAD,
    EXAMPLE_LINE_ITEM_STATE_PAYLOAD
)
from commerce_coordinator.apps.order_fulfillment.clients import OrderFulfillmentAPIClient

TEST_LMS_URL_ROOT = 'https://testserver.com'


@override_settings(
    ORDER_FULFILLMENT_URL_ROOT=TEST_LMS_URL_ROOT
)
class OrderFulfillmentAPIClientTests(CoordinatorOAuthClientTestCase):
    """OrderFulfillmentApiClient tests"""

    url = urljoin_directory(TEST_LMS_URL_ROOT, '/api/fulfill-order')

    def setUp(self):
        self.client = OrderFulfillmentAPIClient()
        self.payload = {**EXAMPLE_LINE_ITEM_STATE_PAYLOAD, **EXAMPLE_FULFILLMENT_SERVICE_REDIRECTION_PAYLOAD}
        self.logging_obj = EXAMPLE_FULFILLMENT_LOGGING_OBJ

    @patch("commerce_coordinator.apps.commercetools.fulfillment_webhook_utils.webhook_caller.HMACWebhookCaller.call")
    def test_fulfill_order_success(self, mock_call):

        self.client.fulfill_order(self.payload)

        mock_call.assert_called_once_with(self.url, self.payload)

    @patch("commerce_coordinator.apps.commercetools.fulfillment_webhook_utils.webhook_caller.HMACWebhookCaller.call")
    def test_fulfill_order_failure(self, mock_call):

        mock_call.side_effect = Exception("Webhook error")

        with self.assertRaises(Exception) as context:
            self.client.fulfill_order(self.payload)

        self.assertIn("Webhook error", str(context.exception))

        mock_call.assert_called_once_with(self.url, self.payload)
