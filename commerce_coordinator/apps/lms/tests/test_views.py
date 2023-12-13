"""
Tests for the LMS (edx-platform) views.
"""
import ddt
from commercetools.platform.models import ProductProjectionPagedSearchResponse as CTProductProjectionPagedSearchResponse
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from mock import patch
from rest_framework import status
from rest_framework.test import APITestCase

from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient
from commerce_coordinator.apps.commercetools.tests.conftest import MonkeyPatch, gen_variant_search_result
from commerce_coordinator.apps.core.constants import ORDER_HISTORY_PER_SYSTEM_REQ_LIMIT

User = get_user_model()


@ddt.ddt
class GetActiveManagementSystemTests(APITestCase):
    url = reverse('lms:payment_page_redirect')


    def setupVariantSearch(self):
        self.variant_search_results = gen_variant_search_result()
        pass

    def get_product_variant_by_course_run(self):
        # noinspection PyUnusedLocal
        # pylint: disable=unused-argument # needed for kwargs
        def _get_product_variant_by_course_run(
            _, cr_name: str
        ) -> CTProductProjectionPagedSearchResponse:
            return self.variant_search_results
        # pylint: enable=unused-argument # needed for kwargs

        return _get_product_variant_by_course_run

    def setUp(self):
        super().setUp()
        self.setupVariantSearch()
        MonkeyPatch.monkey(
            CommercetoolsAPIClient,
            {
                '__init__': lambda _: None,
                'get_product_variant_by_course_run': self.get_product_variant_by_course_run()
            }
        )

    def tearDown(self):
        super().tearDown()
        if MonkeyPatch.is_monkey(CommercetoolsAPIClient):
            MonkeyPatch.unmonkey(CommercetoolsAPIClient)

    @patch('commerce_coordinator.apps.rollout.pipeline.is_redirect_to_commercetools_enabled_for_user')
    def test_run_rollout_pipeline_redirect_to_commercetools_enabled(self, is_redirect_mock):
        breakpoint()
        is_redirect_mock.return_value = True
        response = self.client.get(self.url,
                                   {'sku': ['sku1'], 'course_run_key': 'course-v1:MichiganX+InjuryPreventionX+1T2021'})
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
