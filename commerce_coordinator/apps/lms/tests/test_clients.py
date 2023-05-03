"""
Tests for the lms app API clients.
"""
import logging

from django.test import TestCase, override_settings
from mock import patch

from commerce_coordinator.apps.core.clients import urljoin_directory
from commerce_coordinator.apps.core.tests.utils import CoordinatorOAuthClientTestCase
from commerce_coordinator.apps.lms.clients import LMSAPIClient
from commerce_coordinator.apps.lms.tests.constants import (
    EXAMPLE_FULFILLMENT_REQUEST_PAYLOAD,
    EXAMPLE_FULFILLMENT_RESPONSE_PAYLOAD
)

logger = logging.getLogger(__name__)

TEST_LMS_URL_ROOT = 'https://testserver.com'


@override_settings(
    LMS_URL_ROOT=TEST_LMS_URL_ROOT,
    BACKEND_SERVICE_EDX_OAUTH2_PROVIDER_URL='https://testserver.com/auth'
)
class LMSAPIClientTests(CoordinatorOAuthClientTestCase):
    """LMSAPIClient tests."""

    def setUp(self):
        self.client = LMSAPIClient()

    def test_order_create_success(self):
        url = urljoin_directory(TEST_LMS_URL_ROOT, '/api/enrollment/v1/enrollment')
        self.assertJSONClientResponse(
            uut=self.client.enroll_user_in_course,
            input_kwargs={
                'enrollment_data': EXAMPLE_FULFILLMENT_REQUEST_PAYLOAD,
            },
            expected_request=EXAMPLE_FULFILLMENT_REQUEST_PAYLOAD,
            mock_url=url,
            mock_response=EXAMPLE_FULFILLMENT_RESPONSE_PAYLOAD,
            expected_output=EXAMPLE_FULFILLMENT_RESPONSE_PAYLOAD,
        )
