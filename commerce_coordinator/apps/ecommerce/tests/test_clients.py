"""
Tests for the ecommerce app API clients.
"""
import logging

from django.test import override_settings
from requests.exceptions import HTTPError

from commerce_coordinator.apps.core.clients import urljoin_directory
from commerce_coordinator.apps.core.tests.utils import CoordinatorOAuthClientTestCase
from commerce_coordinator.apps.ecommerce.clients import EcommerceAPIClient
from commerce_coordinator.apps.frontend_app_ecommerce.tests import (
    ECOMMERCE_REQUEST_EXPECTED_RESPONSE,
    ORDER_HISTORY_GET_PARAMETERS
)

logger = logging.getLogger(__name__)

TEST_ECOMMERCE_URL = 'https://testserver.com'


@override_settings(
    ECOMMERCE_URL=TEST_ECOMMERCE_URL,
    BACKEND_SERVICE_EDX_OAUTH2_PROVIDER_URL='https://testserver.com/auth'
)
class EcommerceAPIClientTests(CoordinatorOAuthClientTestCase):
    """EcommerceAPIClient tests."""

    api_base_url = urljoin_directory(TEST_ECOMMERCE_URL, '/api/v2/')

    def setUp(self):
        self.client = EcommerceAPIClient()

    def test_get_orders_success(self):
        url = urljoin_directory(self.api_base_url, '/orders')
        self.assertJSONClientResponse(
            uut=self.client.get_orders,
            input_kwargs={
                'query_params': ORDER_HISTORY_GET_PARAMETERS
            },
            expected_request={
                'username': 'TestUser',
                'page': 1,
                'page_size': 20,
                'edx_lms_user_id': 127,
            },
            mock_method='GET',
            mock_url=url,
            mock_response=ECOMMERCE_REQUEST_EXPECTED_RESPONSE,
            expected_output=ECOMMERCE_REQUEST_EXPECTED_RESPONSE,
        )

    def test_get_orders_failure(self):
        '''Check empty request and mock 400 generates exception.'''
        url = urljoin_directory(self.api_base_url, '/orders')
        with self.assertRaises(HTTPError):
            self.assertJSONClientResponse(
                uut=self.client.get_orders,
                input_kwargs={'query_params': ''},
                mock_method='GET',
                mock_url=url,
                mock_status=400,
            )

    def test_refund_for_ios_success(self):
        """Test successful refund_for_ios call."""
        url = urljoin_directory(TEST_ECOMMERCE_URL, 'api/iap/v1/ios/refund/')
        payload = {"order_number": "ORDER123", "amount": "9.99"}
        self.assertJSONClientResponse(
            uut=self.client.refund_for_ios,
            input_kwargs={'payload': payload},
            expected_request=payload,
            mock_method='POST',
            mock_url=url,
            mock_response=None,
            expected_output=None,
        )

    def test_refund_for_ios_failure(self):
        """Test refund_for_ios raises exception on error response."""
        url = urljoin_directory(TEST_ECOMMERCE_URL, 'api/iap/v1/ios/refund/')
        payload = {"order_number": "ORDER123", "amount": "9.99"}
        with self.assertRaises(HTTPError):
            self.assertJSONClientResponse(
                uut=self.client.refund_for_ios,
                input_kwargs={'payload': payload},
                mock_method='POST',
                mock_url=url,
                mock_status=400,
            )
