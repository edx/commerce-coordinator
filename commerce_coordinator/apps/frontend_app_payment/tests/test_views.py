"""
Tests for the frontend_app_payment views.
"""
import copy
import json

import ddt
from django.contrib.auth import get_user_model
from django.urls import reverse
from edx_django_utils.cache import TieredCache
from mock import patch
from rest_framework import status
from rest_framework.test import APITestCase

from commerce_coordinator.apps.core.cache import PaymentCache
from commerce_coordinator.apps.core.constants import PaymentState
from commerce_coordinator.apps.core.tests.utils import name_test
from commerce_coordinator.apps.stripe.constants import StripeErrorCode
from commerce_coordinator.apps.titan.exceptions import NoActiveOrder
from commerce_coordinator.apps.titan.tests.test_clients import (
    ORDER_UUID,
    PROVIDER_RESPONSE_BODY,
    TitanPaymentClientMock,
    titan_active_order_response
)

User = get_user_model()


@ddt.ddt
class GetPaymentViewTests(APITestCase):
    """
    Tests for get payment view.
    """
    # Define test user properties
    test_user_username = 'test'
    test_user_email = 'test@example.com'
    test_user_password = 'secret'
    test_lms_user_id = 1
    url = reverse('frontend_app_payment:get_payment')

    def setUp(self):
        """Create test user before test starts."""
        super().setUp()
        self.user = User.objects.create_user(
            self.test_user_username,
            self.test_user_email,
            self.test_user_password,
            lms_user_id=self.test_lms_user_id,
        )
        TieredCache.dangerous_clear_all_tiers()

    def tearDown(self):
        """Log out any user from client after test ends."""
        super().tearDown()
        self.client.logout()

    def test_view_rejects_session_auth(self):
        """Check Session Auth Not Allowed."""
        # Login
        self.client.login(username=self.test_user_username, password=self.test_user_password)
        # Request get payment
        response = self.client.get(self.url)
        # Error HTTP_401_UNAUTHORIZED
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_view_rejects_unauthorized(self):
        """Check unauthorized users querying payments are getting error"""
        # Logout user
        self.client.logout()
        # Request payment
        response = self.client.get(self.url)
        # Error HTTP_401_UNAUTHORIZED
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @ddt.data(
        name_test("test success", (
            {}, None, status.HTTP_200_OK,
            {}
        )),
        name_test("test order_uuid in required", (
            {}, 'order_uuid', status.HTTP_400_BAD_REQUEST,
            {'error_key': 'order_uuid', 'error_message': 'This field may not be null.'}
        )),
        name_test("test order_uuid format", (
            {'order_uuid': 'invalid-uuid'}, None, status.HTTP_400_BAD_REQUEST,
            {'error_key': 'order_uuid', 'error_message': 'Must be a valid UUID.'}
        )),
        name_test("test payment_number in required.", (
            {}, 'payment_number', status.HTTP_400_BAD_REQUEST,
            {'error_key': 'payment_number', 'error_message': 'This field may not be null.'}
        )),
    )
    @ddt.unpack
    @patch('commerce_coordinator.apps.titan.clients.TitanAPIClient.get_payment', new_callable=TitanPaymentClientMock)
    def test_get_payment(self, update_params, skip_param, expected_status, expected_error, mock_get_payment):
        """
        Ensure data validation and success scenarios for get payment.
        """
        self.client.force_authenticate(user=self.user)
        query_params = {
            'order_uuid': ORDER_UUID,
            'payment_number': 'test-number',
        }
        query_params.update(update_params)

        if skip_param:
            del query_params[skip_param]

        response = self.client.get(self.url, data=query_params)
        self.assertEqual(response.status_code, expected_status)

        response_json = response.json()
        if expected_status == status.HTTP_200_OK:
            self.assertEqual(response_json['state'], PaymentState.PENDING.value)
            self.assertTrue(mock_get_payment.called)
            kwargs = mock_get_payment.call_args.kwargs
            self.assertEqual(kwargs['edx_lms_user_id'], self.test_lms_user_id)
        else:
            expected_error_key = expected_error['error_key']
            expected_error_message = expected_error['error_message']
            self.assertIn(expected_error_key, response_json)
            self.assertIn(expected_error_message, response_json[expected_error_key])

    def _assert_get_payment_api_response(self, query_params, expected_state):
        response = self.client.get(self.url, data=query_params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = response.json()
        self.assertEqual(response_json['state'], expected_state)

    @ddt.data(
        PaymentState.PENDING.value, PaymentState.COMPLETED.value, PaymentState.FAILED.value
    )
    @patch('commerce_coordinator.apps.titan.pipeline.GetTitanPayment.run_filter')
    def test_get_payment_cache(self, payment_state, mock_pipeline):
        """
        Ensure data validation and success scenarios for get payment.
        """
        self.client.force_authenticate(user=self.user)
        payment_number = '12345'
        mock_pipeline.return_value = {
            'payment_data': {
                'payment_number': payment_number,
                'order_uuid': ORDER_UUID,
                'key_id': 'test-code',
                'state': payment_state,
                'provider_response_body': json.loads(PROVIDER_RESPONSE_BODY),
            }
        }
        query_params = {
            'order_uuid': ORDER_UUID,
            'payment_number': payment_number,
        }

        response = self.client.get(self.url, data=query_params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = response.json()
        self.assertEqual(response_json['state'], payment_state)

        # Titan's get_payment endpoint should get hit as there will be no cache first time
        self.assertTrue(mock_pipeline.called)

        # Let call API again, This time we should not be pinging titan as data should be in cache
        mock_pipeline.reset_mock()
        response = self.client.get(self.url, data=query_params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = response.json()
        self.assertEqual(response_json['state'], payment_state)
        self.assertFalse(mock_pipeline.called)

        if payment_state == PaymentState.FAILED.value:
            # there should be new payment number as well.
            self.assertIn('new_payment_number', response_json)
        else:
            self.assertNotIn('new_payment_number', response_json)

    @patch('commerce_coordinator.apps.titan.pipeline.GetTitanPayment.run_filter')
    def test_error_on_unhandled_state(self, mock_pipeline):
        """
        Test scenario if we start getting payment state from titan that we are not expecting in this view.
        """
        self.client.force_authenticate(user=self.user)
        payment_number = '12345'
        mock_pipeline.return_value = {
            'payment_data': {
                'payment_number': payment_number,
                'order_uuid': ORDER_UUID,
                'key_id': 'test-code',
                'state': PaymentState.CHECKOUT.value,
                'provider_response_body': json.loads(PROVIDER_RESPONSE_BODY),
            }
        }
        query_params = {
            'order_uuid': ORDER_UUID,
            'payment_number': payment_number,
        }

        response = self.client.get(self.url, data=query_params)
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    @ddt.data(
        PaymentState.COMPLETED.value, PaymentState.FAILED.value
    )
    @patch('commerce_coordinator.apps.titan.pipeline.GetTitanPayment.run_filter')
    def test_get_payment_cache_flow(self, payment_final_state, mock_pipeline):
        """
        Ensure success scenarios for get payment flow and make sure cache is working as expected.
        """
        self.client.force_authenticate(user=self.user)
        payment_number = '12345'
        payment = {
            'payment_number': payment_number,
            'order_uuid': ORDER_UUID,
            'key_id': 'test-code',
            'state': PaymentState.PENDING.value,
            'provider_response_body': json.loads(PROVIDER_RESPONSE_BODY),
            'new_payment_number': '56789',
        }
        query_params = {
            'order_uuid': '123e4567-e89b-12d3-a456-426614174000',
            'payment_number': payment_number,
        }

        # let's assume payment is in pending state. So there should be PROCESSING cache. API should access it from
        # cache and Titan API should not be called.
        PaymentCache().set_processing_cache_payment(payment)
        self._assert_get_payment_api_response(query_params, PaymentState.PENDING.value)

        # Let's assume, Something happened, and we lost cache. We should get cache restored.
        mock_pipeline.reset_mock()
        TieredCache.dangerous_clear_all_tiers()
        cached_response = PaymentCache().get_processing_cache_payment(payment_number)
        self.assertIsNone(cached_response)
        mock_pipeline.return_value = {'payment_data': payment}
        self._assert_get_payment_api_response(query_params, PaymentState.PENDING.value)
        self.assertTrue(mock_pipeline.called)
        cached_response = PaymentCache().get_processing_cache_payment(payment_number)
        self.assertIsNotNone(cached_response)

        # Now assume Stripe's webhook updated cache to a final state (COMPLETED or FAILED).
        # Coordinator should not call Titan, instead we should get the final result from cache.
        mock_pipeline.reset_mock()
        payment['state'] = payment_final_state
        if payment_final_state == PaymentState.COMPLETED.value:
            PaymentCache().set_paid_cache_payment(payment)
        else:
            #  here payment_final_state is PaymentState.FAILED
            PaymentCache().set_processing_cache_payment(payment)
        self._assert_get_payment_api_response(query_params, expected_state=payment_final_state)
        self.assertFalse(mock_pipeline.called)

        # Let's assume we lost cache again, We should be able to get it from Titan.
        TieredCache.dangerous_clear_all_tiers()
        self._assert_get_payment_api_response(query_params, expected_state=payment_final_state)
        self.assertTrue(mock_pipeline.called)

    @ddt.data(
        StripeErrorCode.CARD_DECLINED.value, None, 'fake-error'
    )
    @patch('commerce_coordinator.apps.titan.pipeline.GetTitanPayment.run_filter')
    def test_stripe_error_code(self, card_error, mock_pipeline):
        """
        Ensure error are returning as expected
        """
        self.client.force_authenticate(user=self.user)
        payment_number = '12345'
        provider_response_body = json.loads(PROVIDER_RESPONSE_BODY)
        provider_response_body['data']['object']['last_payment_error']['code'] = card_error

        payment = {
            'payment_number': payment_number,
            'order_uuid': ORDER_UUID,
            'key_id': 'test-code',
            'state': PaymentState.FAILED.value,
            'provider_response_body': provider_response_body,
        }
        mock_pipeline.return_value = {
            'payment_data': payment
        }
        query_params = {
            'order_uuid': '123e4567-e89b-12d3-a456-426614174000',
            'payment_number': payment_number,
        }
        response = self.client.get(self.url, data=query_params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = response.json()
        if card_error == StripeErrorCode.CARD_DECLINED.value:
            self.assertIn('errors', response_json)
        else:
            self.assertNotIn('errors', response_json)


@ddt.ddt
class DraftPaymentCreateViewTests(APITestCase):
    """
    Tests for create draft payment view.
    """
    # Define test user properties
    test_user_username = 'test'
    test_user_email = 'test@example.com'
    test_user_password = 'secret'
    test_lms_user_id = 1
    url = reverse('frontend_app_payment:create_draft_payment')

    def setUp(self):
        """Create test user before test starts."""
        super().setUp()
        self.user = User.objects.create_user(
            self.test_user_username,
            self.test_user_email,
            self.test_user_password,
            lms_user_id=self.test_lms_user_id,
        )

    def tearDown(self):
        """Log out any user from client after test ends."""
        super().tearDown()
        self.client.logout()

    def test_view_rejects_session_auth(self):
        """Check Session Auth Not Allowed."""
        # Login
        self.client.login(username=self.test_user_username, password=self.test_user_password)
        # Request get payment
        response = self.client.get(self.url)
        # Error HTTP_401_UNAUTHORIZED
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_view_rejects_unauthorized(self):
        """Check unauthorized users creating draft payments are getting error"""
        # Logout user
        self.client.logout()
        # Request payment
        response = self.client.get(self.url)
        # Error HTTP_401_UNAUTHORIZED
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def _assert_draft_payment_create_request(self, expected_response, mock_get_active_order):
        """Asset get"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = response.json()
        self.assertEqual(response_json, expected_response)
        self.assertTrue(mock_get_active_order.called)
        kwargs = mock_get_active_order.call_args.kwargs
        self.assertEqual(kwargs['edx_lms_user_id'], self.test_lms_user_id)

    @patch('commerce_coordinator.apps.titan.clients.TitanAPIClient.get_active_order')
    @patch('commerce_coordinator.apps.titan.clients.TitanAPIClient.create_payment')
    @patch('commerce_coordinator.apps.stripe.clients.StripeAPIClient.create_payment_intent')
    @patch('commerce_coordinator.apps.stripe.clients.StripeAPIClient.retrieve_payment_intent')
    @patch('commerce_coordinator.apps.stripe.clients.StripeAPIClient.update_payment_intent')
    def test_create_payment(
        self,
        mock_update_payment_intent,
        mock_retrieve_payment_intent,
        mock_create_payment_intent,
        mock_create_payment,
        mock_get_active_order
    ):
        """
        Ensure data validation and success scenarios for create draft payment.
        """

        intent_id = 'ch_3MebJMAa00oRYTAV1C26pHmmj572'
        mock_get_active_order_response = copy.deepcopy(titan_active_order_response)
        mock_get_active_order.return_value = mock_get_active_order_response
        mock_create_payment_intent.return_value = {
            'id': intent_id,
            'client_secret': intent_id
        }
        mock_retrieve_payment_intent.return_value = {
            'id': intent_id,
            'client_secret': intent_id
        }
        mock_update_payment_intent.return_value = {
            'number': 'PDHB22WS',
            'orderUuid': ORDER_UUID,
            'referenceNumber': intent_id,
            'state': PaymentState.CHECKOUT.value,
            'providerResponseBody': PROVIDER_RESPONSE_BODY,
        }

        mock_create_payment.return_value = {**mock_get_active_order_response['payments'][0]}

        expected_response = {
            'capture_context': {
                'payment_number': 'PDHB22WS',
                'order_id': ORDER_UUID,
                'key_id': intent_id,
                'state': PaymentState.CHECKOUT.value
            },
        }

        expected_empty_response = {
            'capture_context': {},
        }

        # Test when existing payment exists.
        self._assert_draft_payment_create_request(expected_response, mock_get_active_order)

        # Test when existing payment is Failed.
        mock_get_active_order_response['payments'][0]['state'] = PaymentState.FAILED.value
        self._assert_draft_payment_create_request(expected_response, mock_get_active_order)

        # Test when existing payment is Completed.
        mock_get_active_order_response['payments'][0]['state'] = PaymentState.COMPLETED.value
        self._assert_draft_payment_create_request(expected_empty_response, mock_get_active_order)

        # Test when existing payment does not exist.
        mock_get_active_order_response['payments'] = []
        self._assert_draft_payment_create_request(expected_response, mock_get_active_order)

    @patch('commerce_coordinator.apps.titan.clients.TitanAPIClient.get_active_order', side_effect=NoActiveOrder)
    @patch('commerce_coordinator.apps.titan.clients.TitanAPIClient.create_payment')
    @patch('commerce_coordinator.apps.stripe.clients.StripeAPIClient.create_payment_intent')
    def test_create_payment_no_active_order(
        self,
        mock_create_payment_intent,
        mock_create_payment,
        mock_get_active_order
    ):
        """
        Ensure data validation and success scenarios for create draft payment.
        """

        intent_id = 'ch_3MebJMAa00oRYTAV1C26pHmmj572'
        mock_get_active_order_response = copy.deepcopy(titan_active_order_response)
        mock_get_active_order.return_value = mock_get_active_order_response
        mock_create_payment_intent.return_value = {
            'id': intent_id,
        }
        mock_create_payment.return_value = {**mock_get_active_order_response['payments'][0]}

        expected_empty_response = {
            'capture_context': {},
        }

        # Test when existing payment exists.
        self._assert_draft_payment_create_request(expected_empty_response, mock_get_active_order)

    def test_create_payment_missing_user_id(self):
        """
        Ensure data validation and success scenarios for create draft payment.
        """
        self.user.lms_user_id = None
        self.user.save()
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response_json = response.json()
        self.assertIn('This field may not be null.', response_json['edx_lms_user_id'])

    @patch('commerce_coordinator.apps.titan.clients.TitanAPIClient.get_active_order')
    def test_create_payment_for_unexpected_payment(self, mock_get_active_order):
        """
        Ensure data validation and success scenarios for create draft payment.
        """
        mock_get_active_order_response = copy.deepcopy(titan_active_order_response)
        mock_get_active_order.return_value = mock_get_active_order_response
        del mock_get_active_order_response['payments'][0]['orderUuid']
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response_json = response.json()
        self.assertIn('This field is required.', response_json['payments'][0]['orderUuid'])


@ddt.ddt
class GetActiveOrderViewTests(APITestCase):
    """
    Tests for get active order view.
    """
    # Define test user properties
    test_user_username = 'test'
    test_user_email = 'test@example.com'
    test_user_password = 'test'
    test_lms_user_id = 1
    url = reverse('frontend_app_payment:get_active_order')

    def setUp(self):
        """Create test user before test starts."""
        super().setUp()
        self.user = User.objects.create_user(
            self.test_user_username,
            self.test_user_email,
            self.test_user_password,
            lms_user_id=self.test_lms_user_id,
        )

    def tearDown(self):
        """Log out any user from client after test ends."""
        super().tearDown()
        self.client.logout()

    def test_view_rejects_session_auth(self):
        """Check Session Auth Not Allowed."""
        # Login
        self.client.login(username=self.test_user_username, password=self.test_user_password)
        # Request get payment
        response = self.client.get(self.url)
        # Error HTTP_401_UNAUTHORIZED
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_view_rejects_unauthorized(self):
        """Check unauthorized users querying payments are getting error"""
        # Logout user
        self.client.logout()
        # Request payment
        response = self.client.get(self.url)
        # Error HTTP_401_UNAUTHORIZED
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('commerce_coordinator.apps.titan.clients.TitanAPIClient.get_active_order')
    def test_get_active_order(self, mock_get_active_order):
        """
        Ensure data validation and success scenarios for get payment.
        """
        mock_get_active_order.return_value = {
            "itemTotal": "100.0",
            "total": "100.0",
            "adjustmentTotal": "0.0",
            "createdAt": "2023-05-25T14:45:18.711Z",
            "updatedAt": "2023-05-25T15:12:07.168Z",
            "completedAt": None,
            "currency": "USD",
            "state": "complete",
            "email": "test@2u.com",
            "uuid": "272705e3-9ffb-4a42-a23b-afbbc18f173b",
            "promoTotal": "0.0",
            "itemCount": 1,
            "paymentState": None,
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
                "stateName": None,
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
                    "referenceNumber": "ch_3MebJMAa00oRYTAV1C26pHmmj572",
                    "state": "checkout",
                    "createdAt": "2023-05-25T15:12:07.165Z",
                    "updatedAt": "2023-05-25T15:12:07.165Z"
                }
            ],
        }

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        response_json = response.json()
        self.assertEqual(response_json['basket_id'], '272705e3-9ffb-4a42-a23b-afbbc18f173b')
        self.assertTrue(mock_get_active_order.called)
        kwargs = mock_get_active_order.call_args.kwargs
        self.assertEqual(kwargs['edx_lms_user_id'], self.test_lms_user_id)


@ddt.ddt
class PaymentProcessViewTests(APITestCase):
    """
    Tests for PaymentProcessView.
    """
    # Define test user properties
    test_user_username = 'test'
    test_user_email = 'test@example.com'
    test_user_password = 'secret'
    test_lms_user_id = 1
    url = reverse('frontend_app_payment:process_payment')

    def setUp(self):
        """Create test user before test starts."""
        super().setUp()
        self.user = User.objects.create_user(
            self.test_user_username,
            self.test_user_email,
            self.test_user_password,
            lms_user_id=self.test_lms_user_id,
        )

    def tearDown(self):
        """Log out any user from client after test ends."""
        super().tearDown()
        self.client.logout()

    def test_view_rejects_session_auth(self):
        """Check Session Auth Not Allowed."""
        # Login
        self.client.login(username=self.test_user_username, password=self.test_user_password)
        # Request get payment
        response = self.client.get(self.url)
        # Error HTTP_401_UNAUTHORIZED
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_view_rejects_unauthorized(self):
        """Check unauthorized users querying payments are getting error"""
        # Logout user
        self.client.logout()
        # Request payment
        response = self.client.get(self.url)
        # Error HTTP_401_UNAUTHORIZED
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @ddt.data(
        name_test("test success", (
            {}, None, status.HTTP_200_OK,
            {}
        )),
        name_test("test order_uuid in required", (
            {}, 'order_uuid', status.HTTP_400_BAD_REQUEST,
            {'error_key': 'order_uuid', 'error_message': 'This field is required.'}
        )),
        name_test("test order_uuid format", (
            {'order_uuid': 'invalid-uuid'}, None, status.HTTP_400_BAD_REQUEST,
            {'error_key': 'order_uuid', 'error_message': 'Must be a valid UUID.'}
        )),
        name_test("test payment_number in required.", (
            {}, 'payment_number', status.HTTP_400_BAD_REQUEST,
            {'error_key': 'payment_number', 'error_message': 'This field is required.'}
        )),
        name_test("test skus in required.", (
            {}, 'skus', status.HTTP_400_BAD_REQUEST,
            {
                'error_key': 'skus',
                'error_message': 'Comma seperated `skus` required.'
            }
        )),
        name_test("test skus by passing it in list format.", (
            {'skus': ['skus-1', 'sku-2']}, None, status.HTTP_400_BAD_REQUEST,
            {
                'error_key': 'skus',
                'error_message': 'Comma seperated `skus` required.'
            }
        )),
    )
    @ddt.unpack
    @patch('commerce_coordinator.apps.frontend_app_payment.views.PaymentProcessingRequested.run_filter')
    def test_get_payment(self, update_params, skip_param, expected_status, expected_error, mock_processing_requested):
        """
        Ensure data validation and success scenarios for get payment.
        """
        mock_processing_requested.return_value = {'url': 'redirect-url'}
        self.client.force_authenticate(user=self.user)
        query_params = {
            'order_uuid': ORDER_UUID,
            'payment_number': 'test-payment-number',
            'payment_intent_id': 'test-intent-id',
            'skus': 'test-sku-1,test-sku-2',
        }
        query_params.update(update_params)

        if skip_param:
            del query_params[skip_param]

        response = self.client.post(self.url, data=query_params, format='json')
        self.assertEqual(response.status_code, expected_status)

        response_json = response.json()
        if expected_status == status.HTTP_200_OK:
            self.assertEqual(response_json['url'], 'redirect-url')
            self.assertTrue(mock_processing_requested.called)
            kwargs = mock_processing_requested.call_args.kwargs
            query_params['edx_lms_user_id'] = self.test_lms_user_id
            query_params['skus'] = query_params['skus'].split(',')
            self.assertEqual(kwargs, query_params)
        else:
            expected_error_key = expected_error['error_key']
            expected_error_message = expected_error['error_message']
            self.assertIn(expected_error_key, response_json)
            self.assertIn(expected_error_message, response_json[expected_error_key])
