"""
Tests for the frontend_app_payment views.
"""

import ddt
from django.contrib.auth import get_user_model
from django.urls import reverse
from edx_django_utils.cache import TieredCache
from mock import patch
from rest_framework import status
from rest_framework.test import APITestCase

from commerce_coordinator.apps.core.tests.utils import name_test
from commerce_coordinator.apps.titan.tests.test_clients import ORDER_UUID

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

    def _assert_get_payment_api_response(self, query_params, expected_state):
        response = self.client.get(self.url, data=query_params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = response.json()
        self.assertEqual(response_json['state'], expected_state)


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
