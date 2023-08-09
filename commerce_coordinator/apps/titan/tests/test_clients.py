"""Test Titan clients."""
from unittest.mock import MagicMock, patch

import ddt
from django.test import override_settings
from requests.exceptions import HTTPError

from commerce_coordinator.apps.core.constants import PaymentMethod, PaymentState
from commerce_coordinator.apps.core.tests.utils import CoordinatorClientTestCase
from commerce_coordinator.apps.titan.clients import TitanAPIClient, urljoin_directory

TITAN_URL = 'https://testserver.com'
TITAN_API_KEY = 'top-secret'

ORDER_UUID = '123e4567-e89b-12d3-a456-426614174000'
DEFAULT_CURRENCY = 'USD'

ORDER_CREATE_DATA = {
    'sku': ['sku1', 'sku_2'],
    'edx_lms_user_id': 1,
    'email': 'edx@example.com',
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


class TitanPaymentClientMock(MagicMock):
    """A mock TitanClient."""
    return_value = {
        'orderUuid': ORDER_UUID,
        'state': PaymentState.PROCESSING.value,
        'referenceNumber': 'test-code',
        'number': 'test-number'
    }


titan_active_order_response = {
        'edxLmsUserId': '1',
        'itemTotal': '100.0',
        'total': '100.0',
        'adjustmentTotal': '0.0',
        'createdAt': '2023-05-25T14:45:18.711Z',
        'updatedAt': '2023-05-25T15:12:07.168Z',
        'completedAt': None,
        'currency': 'USD',
        'state': 'complete',
        'email': 'test@2u.com',
        'uuid': ORDER_UUID,
        'promoTotal': '0.0',
        'itemCount': 1,
        'paymentState': None,
        'paymentTotal': '0.0',
        'user': {
            'firstName': 'test',
            'lastName': 'test',
            'email': 'test@2u.com'
        },
        'billingAddress': {
            'address1': 'test',
            'address2': ' test',
            'city': 'test',
            'company': 'Test',
            'countryIso': 'ZA',
            'firstName': 'test',
            'lastName': 'test',
            'phone': 'n/a',
            'stateName': None,
            'zipcode': '50000'
        },
        'lineItems': [
            {
                'quantity': 1,
                'price': '100.0',
                'currency': 'USD',
                'sku': '64411FA',
                'title': 'Accounting Essentials',
                'courseMode': 'verified'
            }
        ],
        'payments': [
            {
                'amount': '228.0',
                'number': 'PDHB22WS',
                'orderUuid': ORDER_UUID,
                'paymentDate': '2023-05-24T08:45:26.388Z',
                'paymentMethodName': PaymentMethod.STRIPE.value,
                'reference': 'TestOrder-58',
                'referenceNumber': 'ch_3MebJMAa00oRYTAV1C26pHmmj572',
                'state': PaymentState.CHECKOUT.value,
                'createdAt': '2023-05-25T15:12:07.165Z',
                'updatedAt': '2023-05-25T15:12:07.165Z'
            }
        ],
    }


class TitanActiveOrderClientMock(MagicMock):
    """A mock TitanClient"""
    return_value = titan_active_order_response


@override_settings(
    TITAN_URL=TITAN_URL,
    TITAN_API_KEY=TITAN_API_KEY
)
@ddt.ddt
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
    def test_create_order_success(self, mock_add_item, mock_create_cart):
        self.client.create_order(
            ORDER_CREATE_DATA['sku'],
            ORDER_CREATE_DATA['edx_lms_user_id'],
            ORDER_CREATE_DATA['email'],
            ORDER_CREATE_DATA['coupon_code'],
            DEFAULT_CURRENCY
        )
        mock_create_cart.assert_called_with(
            ORDER_CREATE_DATA['edx_lms_user_id'],
            ORDER_CREATE_DATA['email'],
            DEFAULT_CURRENCY
        )
        mock_add_item.assert_called_with(
            ORDER_UUID, ORDER_CREATE_DATA['sku'][-1],
            ORDER_CREATE_DATA['edx_lms_user_id'],
        )

    def test_create_cart_success(self):
        url = urljoin_directory(self.api_base_url, '/cart')
        self.assertJSONClientResponse(
            uut=self.client.create_cart,
            input_kwargs={
                'edx_lms_user_id': 1,
                'email': 'edx@example.com',
            },
            expected_request={
                'data': {
                    'attributes': {
                        'currency': 'USD',
                        'edxLmsUserId': 1,
                        'email': 'edx@example.com',
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
                'edx_lms_user_id': '147',
            },
            expected_request={
                'data': {
                    'attributes': {
                        'orderUuid': 'test-uuid',
                        'courseSku': 'test-sku',
                        'edxLmsUserId': '147',
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

    def test_update_billing_address(self):
        url = urljoin_directory(self.api_base_url, '/checkout/update_billing_address')
        order_uuid = ORDER_UUID
        address_1 = 'test address'
        address_2 = '1'
        city = 'a place'
        company = 'a company'
        country_iso = 'US'
        first_name = 'test'
        last_name = 'mctester'
        phone = '5558675309'
        state_name = 'MA'
        zipcode = '55555'

        mock_response = {
            'data': {
                'attributes': {
                    'address1': address_1,
                    'address2': address_2,
                    'city': city,
                    'company': company,
                    'countryIso': country_iso,
                    'firstName': first_name,
                    'lastName': last_name,
                    'phone': phone,
                    'stateName': state_name,
                    'zipcode': zipcode,
                }
            }
        }
        expected_output = mock_response['data']['attributes']
        # test with all params
        self.assertJSONClientResponse(
            uut=self.client.update_billing_address,
            input_kwargs={
                'order_uuid': order_uuid,
                'address_1': address_1,
                'address_2': address_2,
                'city': city,
                'company': company,
                'country_iso': country_iso,
                'first_name': first_name,
                'last_name': last_name,
                'phone': phone,
                'state_name': state_name,
                'zipcode': zipcode,
            },
            expected_request={
                'data': {
                    'attributes': {
                        'orderUuid': order_uuid,
                        'address1': address_1,
                        'address2': address_2,
                        'city': city,
                        'company': company,
                        'countryIso': country_iso,
                        'firstName': first_name,
                        'lastName': last_name,
                        'phone': phone,
                        'stateName': state_name,
                        'zipcode': zipcode,
                    }
                }
            },
            expected_headers=self.expected_headers,
            mock_method='PATCH',
            mock_url=url,
            mock_response=mock_response,
            expected_output=expected_output,
        )
        # test with only required params
        self.assertJSONClientResponse(
            uut=self.client.update_billing_address,
            input_kwargs={
                'order_uuid': order_uuid,
            },
            expected_request={
                'data': {
                    'attributes': {
                        'orderUuid': order_uuid,
                    }
                }
            },
            expected_headers=self.expected_headers,
            mock_method='PATCH',
            mock_url=url,
            mock_response=mock_response,
            expected_output=expected_output,
        )

    @ddt.data(
        {'key': 'value'},
        None
    )
    def test_update_payment(self, provider_response_body):
        url = urljoin_directory(self.api_base_url, '/payments')
        edx_lms_user_id = 1
        payment_number = '1234'
        payment_state = PaymentState.COMPLETED.value
        reference_number = 'fake_payment_intent'

        input_kwargs = {
            'edx_lms_user_id': edx_lms_user_id,
            'order_uuid': ORDER_UUID,
            'payment_number': payment_number,
            'payment_state': payment_state,
            'reference_number': reference_number,
        }

        expected_request = {
            'data': {
                'attributes': {
                    'edxLmsUserId': edx_lms_user_id,
                    'orderUuid': ORDER_UUID,
                    'paymentNumber': payment_number,
                    'paymentState': payment_state,
                    'referenceNumber': reference_number,
                }
            }
        }

        if provider_response_body:
            input_kwargs['provider_response_body'] = provider_response_body
            expected_request['data']['attributes']['providerResponseBody'] = provider_response_body

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
            input_kwargs=input_kwargs,
            expected_request=expected_request,
            expected_headers=self.expected_headers,
            mock_method='PATCH',
            mock_url=url,
            mock_response=mock_response,
            expected_output=expected_output,
        )

    def test_create_payment(self):
        url = urljoin_directory(self.api_base_url, '/payments')
        payment_method_name = PaymentMethod.STRIPE.value
        reference_number = 'a_stripe_response_code'
        provider_response_body = '{"test_key":"test_value"}'
        reference = 'test_reference'
        amount = 1000
        payment_date = '1686318774'
        source = {"test_key": "test_value"}

        mock_response = {
            'data': {
                'attributes': {
                    'orderUuid': ORDER_UUID,
                    'referenceNumber': reference_number,
                    'paymentMethodName': payment_method_name,
                    'providerResponseBody': provider_response_body,
                }
            }
        }
        expected_output = mock_response['data']['attributes']
        edx_lms_user_id = '628'
        # test with all params
        self.assertJSONClientResponse(
            uut=self.client.create_payment,
            input_kwargs={
                'order_uuid': ORDER_UUID,
                'reference_number': reference_number,
                'payment_method_name': payment_method_name,
                'provider_response_body': provider_response_body,
                'reference': reference,
                'amount': amount,
                'payment_date': payment_date,
                'source': source,
                'edx_lms_user_id': edx_lms_user_id
            },
            expected_request={
                'data': {
                    'attributes': {
                        'orderUuid': ORDER_UUID,
                        'referenceNumber': reference_number,
                        'paymentMethodName': payment_method_name,
                        'providerResponseBody': provider_response_body,
                        'reference': reference,
                        'amount': amount,
                        'paymentDate': payment_date,
                        'source': source,
                        'edxLmsUserId': edx_lms_user_id
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
                'reference_number': reference_number,
                'payment_method_name': payment_method_name,
                'provider_response_body': provider_response_body,
                'edx_lms_user_id': edx_lms_user_id
            },
            expected_request={
                'data': {
                    'attributes': {
                        'orderUuid': ORDER_UUID,
                        'referenceNumber': reference_number,
                        'paymentMethodName': payment_method_name,
                        'providerResponseBody': provider_response_body,
                        'edxLmsUserId': edx_lms_user_id
                    }
                }
            },
            expected_headers=self.expected_headers,
            mock_method='POST',
            mock_url=url,
            mock_response=mock_response,
            expected_output=expected_output,
        )

    def test_get_active_order(self):
        edx_lms_user_id = 1
        url = urljoin_directory(self.api_base_url, f'/accounts/{edx_lms_user_id}/active_order')
        mock_response = {
            "data": {
                "type": "order",
                "attributes": {
                    "edxLmsUserId": '1',
                    "itemTotal": "100.0",
                    "total": "100.0",
                    "adjustmentTotal": "0.0",
                    "createdAt": "2023-05-25T14:45:18.711Z",
                    "updatedAt": "2023-05-25T15:12:07.168Z",
                    "completedAt": "null",
                    "currency": "USD",
                    "state": "complete",
                    "email": "test@2u.com",
                    "uuid": "272705e3-9ffb-4a42-a23b-afbbc18f173b",
                    "promoTotal": "0.0",
                    "itemCount": 1,
                    "paymentState": "null",
                    "paymentTotal": "0.0",
                    "user": {
                        "firstName": "test",
                        "lastName": "test",
                        "email": "test@2u.com"
                    },
                    "billingAddress": {
                        "address1": "test",
                        "address2": " test",
                        "city": "test",
                        "company": "Test",
                        "countryIso": "ZA",
                        "firstName": "test",
                        "lastName": "test",
                        "phone": "n/a",
                        "stateName": "null",
                        "zipcode": "50000"
                    },
                    "lineItems": [
                        {
                            "quantity": 1,
                            "price": "100.0",
                            "currency": "USD",
                            "sku": "64411FA",
                            "title": "Accounting Essentials",
                            "courseMode": "verified"
                        }
                    ],
                    "payments": [
                        {
                            "amount": "228.0",
                            "number": "PDHB22WS",
                            "orderUuid": "272705e3-9ffb-4a42-a23b-afbbc18f173b",
                            "paymentDate": "2023-05-24T08:45:26.388Z",
                            "paymentMethodName": "Stripe",
                            "reference": "TestOrder-58",
                            "responseCode": "ch_3MebJMAa00oRYTAV1C26pHmmj572",
                            "state": "checkout",
                            "createdAt": "2023-05-25T15:12:07.165Z",
                            "updatedAt": "2023-05-25T15:12:07.165Z"
                        }
                    ],
                }
            }
        }

        expected_output = mock_response['data']['attributes']
        self.assertJSONClientResponse(
            uut=self.client.get_active_order,
            input_kwargs={
                'edx_lms_user_id': edx_lms_user_id,
            },
            expected_headers=self.expected_headers,
            mock_method='GET',
            mock_url=url,
            mock_response=mock_response,
            expected_output=expected_output,
        )
