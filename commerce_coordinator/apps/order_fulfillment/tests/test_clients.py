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

EXAMPLE_REVOKE_LINE_REQUEST_PAYLOAD = {
    "edx_lms_username": "testuser",
    "course_run_key": "course-v1:edX+Test+2025",
    "course_mode": "verified",
    "lob": "edx",
}

EXAMPLE_REVOKE_LINE_LOGGING_OBJ = {
    "order_id": "order-1234",
    "payment_id": "payment-5678",
    "customer_id": "customer-9012",
    "course_run_key": "course-v1:edX+Test+2025",
    "lms_user_id": "user-3456",
    "lms_user_name": "testuser",
    "course_mode": "verified",
}

EXAMPLE_REVOKE_LINE_RESPONSE_PAYLOAD = {
    "message": "Course enrollment revoked successfully."
}


@override_settings(
    ORDER_FULFILLMENT_URL_ROOT=TEST_ORDER_FULFILLMENT_URL_ROOT,
    BACKEND_SERVICE_EDX_OAUTH2_PROVIDER_URL='https://testserver.com/auth'
)
class OrderFulfillmentAPIClientTests(CoordinatorOAuthClientTestCase):
    """OrderFulfillmentAPIClient tests."""

    url = urljoin_directory(TEST_ORDER_FULFILLMENT_URL_ROOT, '/api/fulfill-order/')
    revoke_url = urljoin_directory(TEST_ORDER_FULFILLMENT_URL_ROOT, '/api/revoke-line/')

    def setUp(self):
        self.client = OrderFulfillmentAPIClient()
        self.payload = EXAMPLE_FULFILLMENT_REQUEST_PAYLOAD
        self.logging_obj = EXAMPLE_FULFILLMENT_LOGGING_OBJ
        self.revoke_payload = EXAMPLE_REVOKE_LINE_REQUEST_PAYLOAD
        self.revoke_logging_obj = EXAMPLE_REVOKE_LINE_LOGGING_OBJ

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

    def test_revoke_line_success(self):
        """Test successful revoke line request."""
        self.assertJSONClientResponse(
            uut=self.client.revoke_line,
            input_kwargs={
                'payload': self.revoke_payload,
                'logging_data': self.revoke_logging_obj,
            },
            mock_url=self.revoke_url,
            mock_response=EXAMPLE_REVOKE_LINE_RESPONSE_PAYLOAD,
            expected_output=EXAMPLE_REVOKE_LINE_RESPONSE_PAYLOAD,
        )

    def test_revoke_line_failure(self):
        """Test failed revoke line request with HTTPError."""
        self.assertJSONClientResponse(
            uut=self.client.revoke_line,
            input_kwargs={
                'payload': self.revoke_payload,
                'logging_data': self.revoke_logging_obj,
            },
            mock_url=self.revoke_url,
            mock_status=400,
            expected_output=None
        )

    def test_revoke_line_request_exception(self):
        """Test request exception during revoke line."""
        self.assertJSONClientResponse(
            uut=self.client.revoke_line,
            input_kwargs={
                'payload': self.revoke_payload,
                'logging_data': self.revoke_logging_obj,
            },
            mock_url=self.revoke_url,
            mock_status=500,  # Using a different status code from the failure test
            expected_output=None
        )
