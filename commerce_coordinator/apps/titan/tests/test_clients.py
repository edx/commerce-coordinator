"""Test Titan clients."""

from django.test import override_settings

from commerce_coordinator.apps.core.tests.utils import CoordinatorClientTestCase
from commerce_coordinator.apps.titan.clients import TitanAPIClient, urljoin_directory

TITAN_URL = 'https://testserver.com'
TITAN_API_KEY = 'top-secret'


@override_settings(
    TITAN_URL=TITAN_URL,
    TITAN_API_KEY=TITAN_API_KEY
)
class TestTitanAPIClient(CoordinatorClientTestCase):
    """TitanAPIClient tests."""

    expected_headers = {
        'Content-Type': 'application/vnd.api+json',
        'User-Agent': '',
        'X-Spree-API-Key': TITAN_API_KEY,
    }

    def setUp(self):
        self.client = TitanAPIClient()

    def test_order_create_success(self):
        url = urljoin_directory(TITAN_URL, 'edx/api/v1/cart')
        self.assertJSONClientResponse(
            uut=self.client.create_order,
            input_kwargs={
                'edx_lms_user_id': 1,
                'email': 'edx@example.com',
                'first_name': 'John',
                'last_name': 'Doe',
            },
            expected_request={
                'data': {
                    'attributes': {
                        'currency': 'USD',
                        'edxLmsUserId': 1,
                        'email': 'edx@example.com',
                        'firstName': 'John',
                        'lastName': 'Doe',
                    }
                }
            },
            expected_headers=self.expected_headers,
            mock_url=url,
            mock_response={
                'uuid': 'test-uuid',
            },
            expected_output={
                'uuid': 'test-uuid',
            },
        )

    def test_add_item_success(self):
        url = urljoin_directory(TITAN_URL, 'edx/api/v1/cart/add_item')
        self.assertJSONClientResponse(
            uut=self.client.add_item,
            input_kwargs={
                'order_uuid': 'test-uuid',
                'course_sku': 'test-sku',
            },
            expected_request={
                'data': {
                    'attributes': {
                        'orderUuid': 'test-uuid',
                        'courseSku': 'test-sku',
                    }
                }
            },
            expected_headers=self.expected_headers,
            mock_url=url,
            mock_response={
                'uuid': 'test-uuid',
            },
            expected_output={
                'uuid': 'test-uuid',
            },
        )

    def test_order_complete_success(self):
        url = urljoin_directory(TITAN_URL, 'edx/api/v1/checkout/complete')
        self.assertJSONClientResponse(
            uut=self.client.complete_order,
            input_kwargs={
                'order_uuid': 'test-uuid',
                'edx_lms_user_id': 1,
            },
            expected_request={
                'data': {
                    'attributes': {
                        'orderUuid': 'test-uuid',
                        'edxLmsUserId': 1,
                    }
                }
            },
            expected_headers=self.expected_headers,
            mock_url=url,
            mock_response={
                'uuid': 'test-uuid',
            },
            expected_output={
                'uuid': 'test-uuid',
            },
        )

    def test_redeem_enrollment_code_success(self):
        url = urljoin_directory(TITAN_URL, 'edx/api/v1/redeem-enrollment-code')
        self.assertJSONClientResponse(
            uut=self.client.redeem_enrollment_code,
            input_kwargs={
                'coupon_code': 'A1B2C3',
                'email': 'edx@example.com',
                'sku': 'C4D5E6',
                'user_id': 1,
                'username': 'edx',
            },
            expected_request={
                'couponCode': 'A1B2C3',
                'edxLmsUserId': 1,
                'edxLmsUserName': 'edx',
                'email': 'edx@example.com',
                'productSku': 'C4D5E6',
                'source': 'edx'
            },
            expected_headers=self.expected_headers,
            mock_url=url,
            mock_response={
                'uuid': 'test-uuid',
            },
            expected_output={
                'uuid': 'test-uuid',
            },
        )
