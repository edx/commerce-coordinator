"""
Tests for the lms app API clients.
"""
import logging

from django.test import override_settings
from mock import MagicMock, patch
from requests.exceptions import HTTPError

from commerce_coordinator.apps.core.clients import urljoin_directory
from commerce_coordinator.apps.core.tests.utils import CoordinatorOAuthClientTestCase
from commerce_coordinator.apps.lms.clients import DiscoveryAPIClient, LMSAPIClient
from commerce_coordinator.apps.lms.tests.constants import (
    EXAMPLE_ENROLLMENT_FULFILLMENT_REQUEST_PAYLOAD,
    EXAMPLE_FULFILLMENT_LOGGING_OBJ,
    EXAMPLE_FULFILLMENT_RESPONSE_PAYLOAD,
    EXAMPLE_LINE_ITEM_STATE_PAYLOAD
)

logger = logging.getLogger(__name__)

TEST_LMS_URL_ROOT = 'https://testserver.com'
TEST_DISCOVERY_URL_ROOT = 'https://discovery.testserver.com'
TEST_COURSE_UUID = '3bdf1dd1-49be-4a15-9145-38901f578c5a'


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

    url = urljoin_directory(TEST_LMS_URL_ROOT, '/api/enrollment/v1/enrollment')
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
            mock_url=self.url,
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
                mock_url=self.url,
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


@override_settings(
    DISCOVERY_URL_ROOT=TEST_DISCOVERY_URL_ROOT,
    BACKEND_SERVICE_EDX_OAUTH2_PROVIDER_URL='https://testserver.com/auth'
)
class DiscoveryAPIClientTests(CoordinatorOAuthClientTestCase):
    """DiscoveryAPIClient tests."""

    course_run_key = 'course-v1:edX+DemoX+Demo_Course'
    course_run_url = f'{TEST_DISCOVERY_URL_ROOT}/api/v1/course_runs/{course_run_key}/'

    def setUp(self):
        self.client = DiscoveryAPIClient()

    def test_get_course_uuid(self):
        """ Test the course UUID is read from the course run, with the course run key in the URL as it is."""
        self.assertJSONClientResponse(
            uut=self.client.get_course_uuid,
            input_kwargs={'course_run_key': self.course_run_key},
            mock_method='GET',
            mock_url=self.course_run_url,
            mock_response={'key': self.course_run_key, 'course_uuid': TEST_COURSE_UUID},
            expected_output=TEST_COURSE_UUID,
        )

    def test_get_course_uuid_api_error(self):
        """ Test an error of Discovery is raised, so the caller can fall back."""
        with self.assertRaises(HTTPError):
            self.assertJSONClientResponse(
                uut=self.client.get_course_uuid,
                input_kwargs={'course_run_key': self.course_run_key},
                mock_method='GET',
                mock_url=self.course_run_url,
                mock_status=404,
            )
