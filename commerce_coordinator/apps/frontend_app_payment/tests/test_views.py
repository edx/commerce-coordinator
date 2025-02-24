"""
Tests for the frontend_app_payment views.
"""

import ddt
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


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
