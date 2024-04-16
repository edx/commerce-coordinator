'''
Tests for the lms app API clients.
'''
import logging

from django.test import override_settings
from requests.exceptions import HTTPError

from commerce_coordinator.apps.core.clients import urljoin_directory
from commerce_coordinator.apps.core.tests.utils import CoordinatorOAuthClientTestCase
from commerce_coordinator.apps.lms.clients import LMSAPIClient
from commerce_coordinator.apps.lms.tests.constants import (
    EXAMPLE_FULFILLMENT_REQUEST_PAYLOAD,
    EXAMPLE_FULFILLMENT_RESPONSE_PAYLOAD,
    EXAMPLE_LINE_ITEM_STATE_PAYLOAD
)

logger = logging.getLogger(__name__)

TEST_LMS_URL_ROOT = 'https://testserver.com'


@override_settings(
    LMS_URL_ROOT=TEST_LMS_URL_ROOT,
    BACKEND_SERVICE_EDX_OAUTH2_PROVIDER_URL='https://testserver.com/auth'
)
class LMSAPIClientTests(CoordinatorOAuthClientTestCase):
    '''LMSAPIClient tests.'''

    url = urljoin_directory(TEST_LMS_URL_ROOT, '/api/enrollment/v1/enrollment')

    def setUp(self):
        self.client = LMSAPIClient()

    def test_order_create_success(self):
        '''Check EXAMPLE_FULFILLMENT_*_PAYLOAD generates correct request and response.'''
        self.assertJSONClientResponse(
            uut=self.client.enroll_user_in_course,
            input_kwargs={
                'enrollment_data': EXAMPLE_FULFILLMENT_REQUEST_PAYLOAD,
                'line_item_state_payload': EXAMPLE_LINE_ITEM_STATE_PAYLOAD
            },
            expected_request=EXAMPLE_FULFILLMENT_REQUEST_PAYLOAD,
            mock_url=self.url,
            mock_response=EXAMPLE_FULFILLMENT_RESPONSE_PAYLOAD,
            expected_output=EXAMPLE_FULFILLMENT_RESPONSE_PAYLOAD,
        )

    def test_order_create_failure(self):
        '''Check empty request and mock 400 generates exception.'''
        with self.assertRaises(HTTPError):
            self.assertJSONClientResponse(
                uut=self.client.enroll_user_in_course,
                input_kwargs={'enrollment_data': '', 'line_item_state_payload': EXAMPLE_LINE_ITEM_STATE_PAYLOAD},
                mock_url=self.url,
                mock_status=400,
            )
