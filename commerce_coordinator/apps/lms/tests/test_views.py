"""
Tests for the LMS (edx-platform) views.
"""
import ddt
import requests_mock
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from mock import patch
from rest_framework import status
from rest_framework.test import APITestCase

from commerce_coordinator.apps.commercetools.tests.conftest import (
    APITestingSet,
    gen_variant_search_result
)

User = get_user_model()

TEST_ECOMMERCE_URL = 'https://testserver.com'

@ddt.ddt
class GetActiveManagementSystemTests(APITestCase):

    url = reverse('lms:payment_page_redirect')

    def setUp(self) -> None:
        super().setUp()
        self.client_set = APITestingSet.new_instance()

    def tearDownCTApiClient(self) -> None:
        # force deconstructor call or some test get flaky
        del self.client_set
        super().tearDown()

    @patch('commerce_coordinator.apps.rollout.pipeline.is_redirect_to_commercetools_enabled_for_user')
    def test_run_rollout_pipeline_redirect_to_commercetools_enabled(self, is_redirect_mock):
        base_url = self.client_set.get_base_url_from_client()

        # Because the base mocker can't do param binding, we have to intercept.
        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.get(
                f"{base_url}product-projections/search?"
                f"markMatchingVariants=False"
                f"&filter=variants.sku%3A%22course-v1%3AMichiganX%2BInjuryPreventionX%2B1T2021%22",
                json=gen_variant_search_result().serialize()
            )

            ret_variant = self.client_set.client.get_product_variant_by_course_run('course-v1:MichiganX+InjuryPreventionX+1T2021')
            breakpoint()
            is_redirect_mock.return_value = True
            response = self.client.get(self.url, {'sku': ['sku1'], 'course_run_key': 'course-v1:MichiganX+InjuryPreventionX+1T2021'})
            # self.assertIn(ret_variant, response.url)
            self.assertTrue(response.headers['Location'].startswith(settings.COMMERCETOOLS_FRONTEND_URL))

    # @patch('commerce_coordinator.apps.rollout.pipeline.is_redirect_to_commercetools_enabled_for_user')
    # def test_run_filter_only_sku_available(self, is_redirect_mock):
    #     self.client.login(username=self.test_user_username, password=self.test_user_password)
    #     self.client.force_authenticate(user=self.user)
    #     is_redirect_mock.return_value = False
    #     response = self.client.get(self.url, {'sku': ['sku1']})
    #     self.assertTrue(response.headers['Location'].startswith(settings.FRONTEND_APP_PAYMENT_URL))


@ddt.ddt
class PaymentPageRedirectViewTests(APITestCase):
    """
    Tests for payment page redirect view.
    """
    # Define test user properties
    test_user_username = 'test'
    test_user_email = 'test@example.com'
    test_user_password = 'secret'
    url = reverse('lms:payment_page_redirect')

    def setUp(self) -> None:
        super().setUp()
        self.client_set = APITestingSet.new_instance()

    def tearDown(self) -> None:
        # force deconstructor call or some test get flaky
        del self.client_set
        super().tearDown()

    def test_view_rejects_session_auth(self):
        """Check Session Auth Not Allowed."""
        # Login
        self.client.login(username=self.test_user_username, password=self.test_user_password)
        # Request Order create
        response = self.client.get(self.url)
        # Error HTTP_400_BAD_REQUEST
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_view_rejects_unauthorized(self):
        """Check unauthorized users querying orders are redirected to login page."""
        # Logout user
        self.client.logout()
        # Request Order create
        response = self.client.get(self.url)
        # Error HTTP_302_FOUND
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)

    @patch('commerce_coordinator.apps.rollout.pipeline.is_redirect_to_commercetools_enabled_for_user')
    def test_run_rollout_pipeline_redirect_to_commercetools_enabled(self, is_redirect_mock):
        self.client.login(username=self.test_user_username, password=self.test_user_password)
        self.client.force_authenticate(user=self.user)
        is_redirect_mock.return_value = True
        response = self.client.get(self.url, {'sku': ['sku1'], 'course_run_key': 'course_run_key1'})
        self.assertTrue(response.headers['Location'].startswith(settings.COMMERCETOOLS_FRONTEND_URL))

    @override_settings(ECOMMERCE_URL=TEST_ECOMMERCE_URL)
    @patch('commerce_coordinator.apps.rollout.pipeline.is_redirect_to_commercetools_enabled_for_user')
    def test_run_filter_only_sku_available(self, is_redirect_mock):
        self.client.login(username=self.test_user_username, password=self.test_user_password)
        self.client.force_authenticate(user=self.user)
        is_redirect_mock.return_value = False
        response = self.client.get(self.url, {'sku': ['sku1']})
        self.assertTrue(response.headers['Location'].startswith(settings.ECOMMERCE_URL))

    @ddt.unpack
    @patch('commerce_coordinator.apps.rollout.pipeline.is_redirect_to_commercetools_enabled_for_user')
    def test_payment_page_redirect(self, is_redirect_mock):
        is_redirect_mock.return_value = True
        self.client.login(username=self.test_user_username, password=self.test_user_password)

        query_params = {
            'sku': 'sku1',
            'course_run_key': 'course-v1:MichiganX+InjuryPreventionX+1T2021'
        }

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, data=query_params)
        self.assertEqual(response.status_code, status.HTTP_303_SEE_OTHER)
