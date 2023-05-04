"""
Tests for the LMS (edx-platform) views.
"""
import uuid

import ddt
import django.conf
from django.contrib.auth import get_user_model
from django.urls import reverse
from mock import patch
from rest_framework import status
from rest_framework.test import APITestCase

from commerce_coordinator.apps.core.tests.utils import name_test

User = get_user_model()


@ddt.ddt
class OrderCreateViewTests(APITestCase):
    """
    Tests for order create view.
    """
    # Define test user properties
    test_user_username = 'test'
    test_user_email = 'test@example.com'
    test_user_password = 'secret'
    url = reverse('lms:create_order')

    def setUp(self):
        """Create test user before test starts."""
        super().setUp()
        self.user = User.objects.create_user(
            self.test_user_username,
            self.test_user_email,
            self.test_user_password,
            # TODO: Remove is_staff=True
            is_staff=True,
        )

    def tearDown(self):
        """Log out any user from client after test ends."""
        super().tearDown()
        self.client.logout()

    def test_view_rejects_session_auth(self):
        """Check Session Auth Not Allowed."""
        # Login
        self.client.login(username=self.test_user_username, password=self.test_user_password)
        # Request Order create
        response = self.client.get(self.url)
        # Error HTTP_401_UNAUTHORIZED
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_view_rejects_unauthorized(self):
        """Check unauthorized users querying orders are redirected to login page."""
        # Logout user
        self.client.logout()
        # Request Order create
        response = self.client.get(self.url)
        # Error HTTP_401_UNAUTHORIZED
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @ddt.data(
        name_test("test success", (
            {}, None, status.HTTP_303_SEE_OTHER,
            {
                'order_data': None,
                'params': {
                    'coupon_code': 'test_code', 'edx_lms_user_id': 1, 'email': 'pass-by-param@example.com',
                    'first_name': 'John', 'last_name': 'Doe', 'product_sku': ['sku1']
                }
             }
        )),
        name_test("test coupon_code is optional.", (
            {}, 'coupon_code', status.HTTP_303_SEE_OTHER,
            {
                'order_data': None,
                'params': {
                    'coupon_code': None, 'edx_lms_user_id': 1, 'email': 'pass-by-param@example.com',
                    'first_name': 'John', 'last_name': 'Doe', 'product_sku': ['sku1']
                }
             }
        )),
        name_test("test product_sku in required", (
            {}, 'product_sku', status.HTTP_400_BAD_REQUEST,
            {'error_key': 'product_sku', 'error_message': 'This list may not be empty.'}
        )),
        name_test("test edx_lms_user_id in required.", (
            {}, 'edx_lms_user_id', status.HTTP_400_BAD_REQUEST,
            {'error_key': 'edx_lms_user_id', 'error_message': 'This field may not be null.'}
        )),
        name_test("test email in required.", (
            {}, 'email', status.HTTP_400_BAD_REQUEST,
            {'error_key': 'email', 'error_message': 'This field may not be null.'}
        )),
        name_test("test invalid email.", (
            {'email': 'invalid-email'}, None, status.HTTP_400_BAD_REQUEST,
            {
                'error_key': 'email',
                'error_message': 'Enter a valid email address.'
            }
        )),
        name_test("test empty email.", (
            {
                'email': ''
            }, None, status.HTTP_400_BAD_REQUEST,
            {
                'error_key': 'email',
                'error_message': 'This field may not be blank.'
            }
        )),
        name_test("test edx_lms_user_id should be valid integer.", (
            {'edx_lms_user_id': 'invalid-id'}, None, status.HTTP_400_BAD_REQUEST,
            {'error_key': 'edx_lms_user_id', 'error_message': 'A valid integer is required.'}
        )),
    )
    @ddt.unpack
    @patch('commerce_coordinator.apps.titan.signals.order_created_save_task.delay')
    def test_create_order(self, update_params, skip_param, expected_status, expected_error_or_response, _):
        """
        Ensure data validation and success scenarios for order create.
        """

        is_redirect_test = status.HTTP_301_MOVED_PERMANENTLY <= expected_status <= status.HTTP_303_SEE_OTHER

        self.client.force_authenticate(user=self.user)
        query_params = {
            'edx_lms_user_id': 1,
            'product_sku': ['sku1'],
            'coupon_code': 'test_code',
            'email': 'pass-by-param@example.com',
        }

        if is_redirect_test:
            query_params.update({
                'utm_source': uuid.uuid4(),
                'utm_custom': uuid.uuid4(),
            })

        query_params.update(update_params)
        if skip_param:
            del query_params[skip_param]

        response = self.client.get(self.url, data=query_params)
        self.assertEqual(response.status_code, expected_status)

        if is_redirect_test:
            redirect_location: str = response.headers['Location']

            self.assertTrue(redirect_location.startswith(django.conf.settings.PAYMENT_MICROFRONTEND_URL))
            self.assertIn("utm_", redirect_location, "No UTM Params Found")
            self.assertIn(f"utm_source={query_params['utm_source']}", redirect_location, "Std UTM Params Not Found")
            self.assertIn(f"utm_custom={query_params['utm_custom']}", redirect_location, "Custom UTM Params Not Found")
        elif expected_status == status.HTTP_200_OK:
            response_json = response.json()
            args = expected_error_or_response
            self.assertEqual(args, response_json)
        else:
            response_json = response.json()
            expected_error_key = expected_error_or_response['error_key']
            expected_error_message = expected_error_or_response['error_message']
            self.assertIn(expected_error_key, response_json)
            self.assertIn(expected_error_message, response_json[expected_error_key])
