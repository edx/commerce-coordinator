"""
Tests for the ecommerce app API clients.
"""
import logging

from django.test import override_settings

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

    def setUp(self):
        self.client = EcommerceAPIClient()

    def test_order_create_success(self):
        url = TEST_ECOMMERCE_URL + '/api/v2/orders'
        self.assertJSONClientResponse(
            uut=self.client.get_orders,
            input_kwargs={
                'query_params': ORDER_HISTORY_GET_PARAMETERS
            },
            expected_request={
                'username': 'TestUser',
                'page': 1,
                'page_size': 20,
            },
            mock_method='GET',
            mock_url=url,
            mock_response=ECOMMERCE_REQUEST_EXPECTED_RESPONSE,
            expected_output=ECOMMERCE_REQUEST_EXPECTED_RESPONSE,
        )
