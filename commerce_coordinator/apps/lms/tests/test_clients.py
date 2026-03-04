"""
Tests for the lms app API clients.
"""
import logging

import responses
from django.test import override_settings
from mock import MagicMock, patch
from requests.exceptions import HTTPError

from commerce_coordinator.apps.core.clients import urljoin_directory
from commerce_coordinator.apps.core.tests.utils import CoordinatorOAuthClientTestCase
from commerce_coordinator.apps.lms.clients import LMSAPIClient
from commerce_coordinator.apps.lms.tests.constants import (
    EXAMPLE_ENROLLMENT_FULFILLMENT_REQUEST_PAYLOAD,
    EXAMPLE_FULFILLMENT_LOGGING_OBJ,
    EXAMPLE_FULFILLMENT_RESPONSE_PAYLOAD,
    EXAMPLE_LINE_ITEM_STATE_PAYLOAD
)

logger = logging.getLogger(__name__)

TEST_LMS_URL_ROOT = 'https://testserver.com'


class FulfillmentCompletedUpdateCTLineItemSignalMock(MagicMock):
    """
    A mock fulfillment_completed_update_ct_line_item_signal
    """

    def mock_receiver(self):
        pass  # pragma: no cover

    return_value = [
        (mock_receiver, ''),
    ]


@override_settings(
    LMS_URL_ROOT=TEST_LMS_URL_ROOT,
    BACKEND_SERVICE_EDX_OAUTH2_PROVIDER_URL='https://testserver.com/auth'
)
class LMSAPIClientTests(CoordinatorOAuthClientTestCase):
    """LMSAPIClient tests."""

    enrollment_url = urljoin_directory(TEST_LMS_URL_ROOT, '/api/enrollment/v1/enrollment')
    entitlement_url = urljoin_directory(TEST_LMS_URL_ROOT, '/api/entitlements/v1/entitlements/')
    deactivate_user_url = urljoin_directory(TEST_LMS_URL_ROOT, '/api/user/v1/accounts/{username}/deactivate/')

    def setUp(self):
        self.client = LMSAPIClient()

    @patch('commerce_coordinator.apps.lms.clients.fulfillment_completed_update_ct_line_item_signal.send_robust',
           new_callable=FulfillmentCompletedUpdateCTLineItemSignalMock)
    def test_order_create_success(self, mock_signal):
        """Check EXAMPLE_FULFILLMENT_*_PAYLOAD generates correct request and response."""
        self.assertJSONClientResponse(
            uut=self.client.enroll_user_in_course,
            input_kwargs={
                'enrollment_data': EXAMPLE_ENROLLMENT_FULFILLMENT_REQUEST_PAYLOAD,
                'line_item_state_payload': EXAMPLE_LINE_ITEM_STATE_PAYLOAD,
                'fulfillment_logging_obj': EXAMPLE_FULFILLMENT_LOGGING_OBJ
            },
            expected_request=EXAMPLE_ENROLLMENT_FULFILLMENT_REQUEST_PAYLOAD,
            mock_url=self.enrollment_url,
            mock_response=EXAMPLE_FULFILLMENT_RESPONSE_PAYLOAD,
            expected_output=EXAMPLE_FULFILLMENT_RESPONSE_PAYLOAD,
        )
        mock_signal.assert_called_once()

    @patch('commerce_coordinator.apps.lms.clients.fulfillment_completed_update_ct_line_item_signal.send_robust',
           new_callable=FulfillmentCompletedUpdateCTLineItemSignalMock)
    def test_order_create_failure(self, mock_signal):
        """Check empty request and mock 400 generates exception."""
        with self.assertRaises(HTTPError):
            self.assertJSONClientResponse(
                uut=self.client.enroll_user_in_course,
                input_kwargs={
                    'enrollment_data': '',
                    'line_item_state_payload': EXAMPLE_LINE_ITEM_STATE_PAYLOAD,
                    'fulfillment_logging_obj': EXAMPLE_FULFILLMENT_LOGGING_OBJ
                },
                mock_url=self.enrollment_url,
                mock_status=400,
            )
        mock_signal.assert_called_once()

    def test_deactivate_user(self):
        """ Test deactivate user in LMS request and response."""
        self.assertJSONClientResponse(
            uut=self.client.deactivate_user,
            input_kwargs={
                'username': 'test_user',
                'ct_message_id': 'mock_message_id'
            },
            mock_url=self.deactivate_user_url.format(username='test_user', ct_message_id='mock_message_id'),
        )

    def test_deactivate_user_api_error(self):
        """ Test deactivate user in LMS request and response."""
        with self.assertRaises(HTTPError):
            self.assertJSONClientResponse(
                uut=self.client.deactivate_user,
                input_kwargs={
                    'username': 'test_user',
                    'ct_message_id': 'mock_message_id'
                },
                mock_url=self.deactivate_user_url.format(username='test_user', ct_message_id='mock_message_id'),
                mock_status=400,
            )

    def test_expire_entitlement(self):
        """Test expire entitlement in LMS request and response"""
        mock_entitlement_id = '732b2ef1-b6c3-4888-855c-2ccfd5d79cf9'
        mock_url = f"{self.entitlement_url}{mock_entitlement_id}/"
        responses.add(method='DELETE', url=mock_url)

        self.assertJSONClientResponse(
            uut=self.client.expire_entitlement,
            input_kwargs={
                'entitlement_id': mock_entitlement_id,
                'fulfillment_logging_obj': EXAMPLE_FULFILLMENT_LOGGING_OBJ
            },
            mock_method='DELETE',
            mock_url=mock_url,
            mock_status=204,
            expected_output={}
        )

    def test_expire_entitlement_error(self):
        """Test expire entitlement in LMS request and response"""
        mock_entitlement_id = 'invalid-uuid'
        mock_url = f"{self.entitlement_url}{mock_entitlement_id}/"

        with self.assertRaises(HTTPError):
            self.assertJSONClientResponse(
                uut=self.client.expire_entitlement,
                input_kwargs={
                    'entitlement_id': mock_entitlement_id,
                    'fulfillment_logging_obj': EXAMPLE_FULFILLMENT_LOGGING_OBJ
                },
                mock_method='DELETE',
                mock_url=mock_url,
                mock_status=404,
            )
