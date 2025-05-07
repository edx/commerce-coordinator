"""
Tests for the Order Fulfillment API client.
"""
from django.test import override_settings
from requests.exceptions import HTTPError, RequestException

from commerce_coordinator.apps.core.clients import urljoin_directory
from commerce_coordinator.apps.core.tests.utils import CoordinatorOAuthClientTestCase
from commerce_coordinator.apps.order_fulfillment.clients import OrderFulfillmentAPIClient

TEST_ORDER_FULFILLMENT_URL_ROOT = 'https://testserver.com'

EXAMPLE_FULFILLMENT_REQUEST_PAYLOAD = {
    "order_id": "1234",
    "course_id": "course-v1:edX+Test+2025",
    "user_id": "user-abc",
}

EXAMPLE_FULFILLMENT_LOGGING_OBJ = {
    "user_id": "user-abc",
    "edx_lms_username": "testuser",
    "order_id": "1234",
    "course_id": "course-v1:edX+Test+2025",
    "message_id": "msg-5678",
    "celery_task_id": "task-0001",
}

EXAMPLE_FULFILLMENT_RESPONSE_PAYLOAD = {
    "message": "Fulfillment request sent to LMS."
}


@override_settings(
    ORDER_FULFILLMENT_URL_ROOT=TEST_ORDER_FULFILLMENT_URL_ROOT,
    BACKEND_SERVICE_EDX_OAUTH2_PROVIDER_URL='https://testserver.com/auth'
)
class OrderFulfillmentAPIClientTests(CoordinatorOAuthClientTestCase):
    """OrderFulfillmentAPIClient tests."""

    url = urljoin_directory(TEST_ORDER_FULFILLMENT_URL_ROOT, '/api/fulfill-order/')

    def setUp(self):
        self.client = OrderFulfillmentAPIClient()
        self.payload = EXAMPLE_FULFILLMENT_REQUEST_PAYLOAD
        self.logging_obj = EXAMPLE_FULFILLMENT_LOGGING_OBJ

    def test_fulfill_order_success(self):
        """Test successful fulfillment request."""
        self.assertJSONClientResponse(
            uut=self.client.fulfill_order,
            input_kwargs={
                'payload': self.payload,
                'logging_data': self.logging_obj,
            },
            mock_url=self.url,
            mock_response=EXAMPLE_FULFILLMENT_RESPONSE_PAYLOAD,
            expected_output=EXAMPLE_FULFILLMENT_RESPONSE_PAYLOAD,
        )

    def test_fulfill_order_failure(self):
        """Test failed fulfillment request with HTTPError."""
        self.assertJSONClientResponse(
            uut=self.client.fulfill_order,
            input_kwargs={
                'payload': self.payload,
                'logging_data': self.logging_obj,
            },
            mock_url=self.url,
            mock_status=400,
            expected_output=None
        )

    def test_fulfill_order_request_exception(self):
        """Test request exception during fulfillment."""
        self.assertJSONClientResponse(
            uut=self.client.fulfill_order,
            input_kwargs={
                'payload': self.payload,
                'logging_data': self.logging_obj,
            },
            mock_url=self.url,
            mock_status=400,
            expected_output=None
        )
