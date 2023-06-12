"""Test Titan clients."""
from unittest.mock import MagicMock, patch

from django.test import override_settings
from requests.exceptions import HTTPError

from commerce_coordinator.apps.core.constants import PaymentMethod, PaymentState
from commerce_coordinator.apps.core.tests.utils import CoordinatorClientTestCase
from commerce_coordinator.apps.titan.clients import TitanAPIClient, urljoin_directory

TITAN_URL = 'https://testserver.com'
TITAN_API_KEY = 'top-secret'

ORDER_UUID = 'test-uuid'
DEFAULT_CURRENCY = 'USD'

ORDER_CREATE_DATA = {
    'product_sku': ['sku1', 'sku_2'],
    'edx_lms_user_id': 1,
    'email': 'edx@example.com',
    'first_name': 'John',
    'last_name': 'Doe',
    'coupon_code': 'test_code',
}

ORDER_CREATE_DATA_WITH_CURRENCY = {'currency': DEFAULT_CURRENCY, **ORDER_CREATE_DATA}


class TitanClientMock(MagicMock):
    """A mock TitanClient."""
    return_value = {
        'data': {
            'attributes': {
                'uuid': ORDER_UUID,
            },
        },
    }


@override_settings(
    TITAN_URL=TITAN_URL,
    TITAN_API_KEY=TITAN_API_KEY
)
class TestTitanAPIClient(CoordinatorClientTestCase):
    """TitanAPIClient tests."""

    api_base_url = urljoin_directory(TITAN_URL, '/edx/api/v1/')

    expected_headers = {
        'Content-Type': 'application/vnd.api+json',
        'User-Agent': '',
        'X-Spree-API-Key': TITAN_API_KEY,
    }

    def setUp(self):
        self.client = TitanAPIClient()

    def test_post_failure(self):
        '''Check empty request and mock 400 generates exception.'''
        with self.assertRaises(HTTPError):
            self.assertJSONClientResponse(
                uut=self.client._request,  # pylint: disable=protected-access
                input_kwargs={'request_method': 'POST', 'resource_path': '/'},
                mock_url=self.api_base_url,
                mock_status=400,
            )

    #
    @patch('commerce_coordinator.apps.titan.clients.TitanAPIClient.create_cart', new_callable=TitanClientMock)
    @patch('commerce_coordinator.apps.titan.clients.TitanAPIClient.add_item', new_callable=TitanClientMock)
    @patch('commerce_coordinator.apps.titan.clients.TitanAPIClient.complete_order', new_callable=TitanClientMock)
    def test_create_order_success(self, mock_complete_order, mock_add_item, mock_create_cart):
        self.client.create_order(
            ORDER_CREATE_DATA['product_sku'],
            ORDER_CREATE_DATA['edx_lms_user_id'],
            ORDER_CREATE_DATA['email'],
            ORDER_CREATE_DATA['first_name'],
            ORDER_CREATE_DATA['last_name'],
            ORDER_CREATE_DATA['coupon_code'],
            DEFAULT_CURRENCY
        )
        mock_create_cart.assert_called_with(
            ORDER_CREATE_DATA['edx_lms_user_id'],
            ORDER_CREATE_DATA['email'],
            ORDER_CREATE_DATA['first_name'],
            ORDER_CREATE_DATA['last_name'],
            DEFAULT_CURRENCY
        )
        mock_add_item.assert_called_with(
            ORDER_UUID, ORDER_CREATE_DATA['product_sku'][-1]
        )
        mock_complete_order.assert_called_with(
            ORDER_UUID, ORDER_CREATE_DATA['edx_lms_user_id']
        )

    def test_create_cart_success(self):
        url = urljoin_directory(self.api_base_url, '/cart')
        self.assertJSONClientResponse(
            uut=self.client.create_cart,
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
        url = urljoin_directory(self.api_base_url, '/cart/add_item')
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
        url = urljoin_directory(self.api_base_url, '/checkout/complete')
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
        url = urljoin_directory(self.api_base_url, '/redeem-enrollment-code')
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

    def test_get_payment(self):
        url = urljoin_directory(self.api_base_url, '/payments')
        mock_response = {
            'data': {
                'attributes': {
                    'orderUuid': 'test-uuid',
                    'state': PaymentState.FAILED.value,

                }
            }
        }
        expected_output = {
            'orderUuid': 'test-uuid',
            'state': PaymentState.FAILED.value,

        }

        # test with no params
        with self.assertRaises(RuntimeError) as ex:
            self.assertJSONClientResponse(
                uut=self.client.get_payment,
                input_kwargs={},
                mock_method='GET',
                mock_url=url,
            )
        self.assertEqual(str(ex.exception), 'payment_number or edx_lms_user_id should be passed as param.')

        # test with edx_lms_user_id only
        self.assertJSONClientResponse(
            uut=self.client.get_payment,
            input_kwargs={
                'edx_lms_user_id': 1,
            },
            expected_request={
                'edxLmsUserId': 1,
            },
            expected_headers=self.expected_headers,
            mock_method='GET',
            mock_url=url,
            mock_response=mock_response,
            expected_output=expected_output,
        )

        # test with payment_number only
        self.assertJSONClientResponse(
            uut=self.client.get_payment,
            input_kwargs={
                'payment_number': '1234',
            },
            expected_request={
                'paymentNumber': '1234',
            },
            expected_headers=self.expected_headers,
            mock_method='GET',
            mock_url=url,
            mock_response=mock_response,
            expected_output=expected_output,
        )

        # test with both params
        self.assertJSONClientResponse(
            uut=self.client.get_payment,
            input_kwargs={
                'edx_lms_user_id': 1,
                'payment_number': '1234',
            },
            expected_request={
                'edxLmsUserId': 1,
                'paymentNumber': '1234',
            },
            expected_headers=self.expected_headers,
            mock_method='GET',
            mock_url=url,
            mock_response=mock_response,
            expected_output=expected_output,
        )

    def test_update_payment(self):
        url = urljoin_directory(self.api_base_url, '/payments')
        payment_number = '1234'
        payment_state = PaymentState.COMPLETED.value
        response_code = 'a_stripe_response_code'

        mock_response = {
            'data': {
                'attributes': {
                    'number': payment_number,
                    'orderUuid': 'test-uuid',
                    'state': payment_state,

                }
            }
        }
        expected_output = mock_response['data']['attributes']

        self.assertJSONClientResponse(
            uut=self.client.update_payment,
            input_kwargs={
                'payment_number': payment_number,
                'payment_state': payment_state,
                'response_code': response_code,
            },
            expected_request={
                'data': {
                    'attributes': {
                        'paymentNumber': payment_number,
                        'paymentState': payment_state,
                        'responseCode': response_code,
                    }
                }
            },
            expected_headers=self.expected_headers,
            mock_method='PATCH',
            mock_url=url,
            mock_response=mock_response,
            expected_output=expected_output,
        )

    def test_create_payment(self):
        url = urljoin_directory(self.api_base_url, '/payments')
        payment_method_name = PaymentMethod.STRIPE.value
        response_code = 'a_stripe_response_code'
        provider_response_body = '{"test_key":"test_value"}'
        reference = 'test_reference'
        amount = 1000
        payment_date = '1686318774'
        source = {"test_key": "test_value"}

        mock_response = {
            'data': {
                'attributes': {
                    'orderUuid': ORDER_UUID,
                    'responseCode': response_code,
                    'paymentMethodName': payment_method_name,
                    'providerResponseBody': provider_response_body,
                }
            }
        }
        expected_output = mock_response['data']['attributes']

        # test with all params
        self.assertJSONClientResponse(
            uut=self.client.create_payment,
            input_kwargs={
                'order_uuid': ORDER_UUID,
                'response_code': response_code,
                'payment_method_name': payment_method_name,
                'provider_response_body': provider_response_body,
                'reference': reference,
                'amount': amount,
                'payment_date': payment_date,
                'source': source,
            },
            expected_request={
                'data': {
                    'attributes': {
                        'orderUuid': ORDER_UUID,
                        'responseCode': response_code,
                        'paymentMethodName': payment_method_name,
                        'providerResponseBody': provider_response_body,
                        'reference': reference,
                        'amount': amount,
                        'paymentDate': payment_date,
                        'source': source,
                    }
                }
            },
            expected_headers=self.expected_headers,
            mock_method='POST',
            mock_url=url,
            mock_response=mock_response,
            expected_output=expected_output,
        )

        # Test with only required params.
        self.assertJSONClientResponse(
            uut=self.client.create_payment,
            input_kwargs={
                'order_uuid': ORDER_UUID,
                'response_code': response_code,
                'payment_method_name': payment_method_name,
                'provider_response_body': provider_response_body,
            },
            expected_request={
                'data': {
                    'attributes': {
                        'orderUuid': ORDER_UUID,
                        'responseCode': response_code,
                        'paymentMethodName': payment_method_name,
                        'providerResponseBody': provider_response_body,
                    }
                }
            },
            expected_headers=self.expected_headers,
            mock_method='POST',
            mock_url=url,
            mock_response=mock_response,
            expected_output=expected_output,
        )
