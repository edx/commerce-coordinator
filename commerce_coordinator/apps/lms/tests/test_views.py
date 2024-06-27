"""
Tests for the LMS (edx-platform) views.
"""
import copy
from urllib.parse import unquote

import ddt
import requests_mock
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from mock import patch
from openedx_filters.exceptions import OpenEdxFilterException
from rest_framework import status
from rest_framework.test import APITestCase

from commerce_coordinator.apps.commercetools.tests.conftest import APITestingSet, gen_variant_search_result
from commerce_coordinator.apps.core.tests.utils import name_test

User = get_user_model()

TEST_ECOMMERCE_URL = 'https://testserver.com'


@override_settings(BACKEND_SERVICE_EDX_OAUTH2_PROVIDER_URL='https://testserver.com/auth')
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
        super().setUp()
        self.client_set = APITestingSet.new_instance()
        self.user = User.objects.create_user(
            self.test_user_username,
            self.test_user_email,
            self.test_user_password,
            # TODO: Remove is_staff=True
            is_staff=True,
        )

    def tearDown(self):
        # force deconstructor call or some test get flaky
        del self.client_set
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

    # TODO: FIX Per SONIC-354
    # @patch('commerce_coordinator.apps.rollout.pipeline.logger')
    # @patch('commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient')
    # def test_get_product_variant_by_course_run_failure(self, mock_ct_client, mock_logger):
    #     self.client.login(username=self.test_user_username, password=self.test_user_password)
    #     self.client.force_authenticate(user=self.user)
    #
    #     mock_ct_client.return_value.get_product_variant_by_course_run.side_effect = HTTPError('Error in CT search')
    #     self.client.get(
    #         self.url,
    #         {'sku': ['sku1'], 'course_run_key': 'course-v1:MichiganX+InjuryPreventionX+1T2021'}
    #     )
    #
    #     mock_logger.exception.assert_called_once_with(
    #         '[get_product_variant_by_course_run] Failed to get CT course for course_run: '
    #         'course-v1:MichiganX+InjuryPreventionX+1T2021 with exception: Error in CT search'
    #     )
    #
    #     mock_ct_client.reset_mock(return_value=True, side_effect=True)

    @patch('commerce_coordinator.apps.rollout.pipeline.is_user_enterprise_learner')
    @patch('commerce_coordinator.apps.rollout.pipeline.is_redirect_to_commercetools_enabled_for_user')
    def test_run_rollout_pipeline_redirect_to_commercetools(self, is_redirect_mock, is_enterprise_mock):
        base_url = self.client_set.get_base_url_from_client()
        self.client.login(username=self.test_user_username, password=self.test_user_password)
        # Because the base mocker can't do param binding, we have to intercept.
        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.get(
                f"{base_url}product-projections/search?"
                f"markMatchingVariants=False"
                f"&filter=variants.sku%3A%22course-v1%3AMichiganX%2BInjuryPreventionX%2B1T2021%22",
                json=gen_variant_search_result().serialize()
            )

            ret_variant = self.client_set.client.get_product_variant_by_course_run(
                'course-v1:MichiganX+InjuryPreventionX+1T2021'
            )
            is_redirect_mock.return_value = True
            is_enterprise_mock.return_value = False
            self.client.force_authenticate(user=self.user)
            response = self.client.get(
                self.url,
                {'sku': ['sku1'], 'course_run_key': 'course-v1:MichiganX+InjuryPreventionX+1T2021'}
            )
            self.assertTrue(response.url.startswith(settings.COMMERCETOOLS_FRONTEND_URL))
            self.assertIn(ret_variant.sku, unquote(unquote(response.url)))

    @patch('commerce_coordinator.apps.rollout.pipeline.is_redirect_to_commercetools_enabled_for_user')
    def test_run_filter_only_sku_available(self, is_redirect_mock):
        self.client.login(username=self.test_user_username, password=self.test_user_password)
        is_redirect_mock.return_value = False
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {'sku': ['sku1']})
        self.assertTrue(response.url.startswith(settings.ECOMMERCE_URL))

    @ddt.unpack
    @patch('commerce_coordinator.apps.rollout.pipeline.is_redirect_to_commercetools_enabled_for_user')
    def test_payment_page_redirect(self, is_redirect_mock):
        base_url = self.client_set.get_base_url_from_client()
        self.client.login(username=self.test_user_username, password=self.test_user_password)
        # Because the base mocker can't do param binding, we have to intercept.
        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.get(
                f"{base_url}product-projections/search?"
                f"markMatchingVariants=False"
                f"&filter=variants.sku%3A%22course-v1%3AMichiganX%2BInjuryPreventionX%2B1T2021%22",
                json=gen_variant_search_result().serialize()
            )
            is_redirect_mock.return_value = True
            self.client.login(username=self.test_user_username, password=self.test_user_password)
            self.client.force_authenticate(user=self.user)
            response = self.client.get(
                self.url,
                {'sku': ['sku1'], 'course_run_key': 'course-v1:MichiganX+InjuryPreventionX+1T2021'}
            )
            self.assertEqual(response.status_code, status.HTTP_303_SEE_OTHER)


@override_settings(COMMERCETOOLS_MERCHANT_CENTER_ORDERS_PAGE_URL='https://merchant-centre/orders')
class OrderDetailsRedirectView(APITestCase):
    """
    Tests for order details page redirect view.
    """
    # Define test user properties
    test_user_username = 'test'
    test_user_email = 'test@example.com'
    test_user_password = 'secret'
    url = reverse('lms:order_details_page_redirect')

    def setUp(self):
        super().setUp()
        self.client_set = APITestingSet.new_instance()
        self.user = User.objects.create_user(
            self.test_user_username,
            self.test_user_email,
            self.test_user_password,
            is_staff=True,
        )

    def tearDown(self):
        # force destructor call or some test get flaky
        del self.client_set
        super().tearDown()
        self.client.logout()

    def test_missing_query_params(self):
        """Check bad request."""
        self.client.login(username=self.test_user_username, password=self.test_user_password)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_legacy_ecommerce_redirect(self):
        self.client.login(username=self.test_user_username, password=self.test_user_password)
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {'order_number': ['EDX-123456']})
        self.assertTrue(response.url.startswith(settings.ECOMMERCE_URL))

    def test_commercetools_redirect(self):
        self.client.login(username=self.test_user_username, password=self.test_user_password)
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {'order_number': ['2U-123456']})
        self.assertTrue(response.url.startswith(settings.COMMERCETOOLS_MERCHANT_CENTER_ORDERS_PAGE_URL))


@ddt.ddt
class RefundViewTests(APITestCase):
    """
    Tests for order refund view.
    """
    # Define test user properties

    test_user_username = 'test'
    test_user_email = 'test@example.com'
    test_user_password = 'secret'

    url = reverse('lms:refund')

    valid_payload = {
        'course_id': 'course-v1:edX+DemoX+Demo_Course',
        'username': 'john',
        'enrollment_attributes': [{
            'namespace': 'order',
            'name': 'order_id',
            'value': '123'
        }, {
            'namespace': 'order',
            'name': 'line_item_id',
            'value': '123'
        }]
    }

    invalid_payload = {
        'course_id': '',
        'username': ''
    }

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            self.test_user_username,
            self.test_user_email,
            self.test_user_password,
            is_staff=True,
        )

    def tearDown(self):
        super().tearDown()
        self.client.logout()

    def authenticate_user(self):
        self.client.login(username=self.test_user_username, password=self.test_user_password)
        self.client.force_authenticate(user=self.user)

    @patch('commerce_coordinator.apps.lms.views.OrderRefundRequested.run_filter')
    def test_post_with_valid_data_succeeds(self, mock_filter):
        self.authenticate_user()
        mock_filter.return_value = {'returned_order': True}
        response = self.client.post(self.url, self.valid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_filter.assert_called_once_with('123', '123')

    @patch('commerce_coordinator.apps.lms.views.OrderRefundRequested.run_filter')
    def test_post_with_valid_data_invalid_pipeline_return_fails(self, mock_filter):
        self.authenticate_user()
        mock_filter.return_value = {'returned_order': None}
        response = self.client.post(self.url, self.valid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_filter.assert_called_once_with('123', '123')

    def test_post_with_invalid_data_fails(self):
        self.authenticate_user()
        response = self.client.post(self.url, self.invalid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('commerce_coordinator.apps.lms.views.OrderRefundRequested.run_filter')
    def test_post_with_filter_exception_fails(self, mock_filter):
        self.authenticate_user()
        mock_filter.side_effect = OpenEdxFilterException('Filter failed')
        response = self.client.post(self.url, self.valid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    @patch('commerce_coordinator.apps.lms.views.OrderRefundRequested.run_filter')
    def test_post_with_unexpected_exception_fails(self, mock_filter):
        self.authenticate_user()
        mock_filter.side_effect = Exception('Unexpected error')
        response = self.client.post(self.url, self.valid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    @ddt.data(
        name_test("missing order_id", (
            "order_id",
        )),
        name_test("missing line_item_id", (
            "line_item_id",
        )),
    )
    @ddt.unpack
    def test_post_with_invalid_attr_data_fails(self, drop_key):
        self.authenticate_user()
        local_invalid_payload = copy.deepcopy(self.valid_payload)
        local_invalid_payload['enrollment_attributes'] = list(
            filter(
                lambda x: x['name'] != drop_key,
                local_invalid_payload['enrollment_attributes']
            )
        )
        response = self.client.post(self.url, local_invalid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


@ddt.ddt
class RetirementViewTests(APITestCase):
    """
    Tests for user retirement view.
    """

    test_user_username = 'test'
    test_user_email = 'test@example.com'
    test_user_password = 'secret'

    url = reverse('lms:user_retirement')

    valid_payload = {
        'edx_lms_user_id': 127,
    }

    invalid_payload = {
        'edx_lms_user_id': '',
    }

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            self.test_user_username,
            self.test_user_email,
            self.test_user_password,
            is_staff=True,
        )

    def tearDown(self):
        super().tearDown()
        self.client.logout()

    def authenticate_user(self):
        self.client.login(username=self.test_user_username, password=self.test_user_password)
        self.client.force_authenticate(user=self.user)

    @patch('commerce_coordinator.apps.lms.views.UserRetirementRequested.run_filter')
    def test_post_with_valid_data_succeeds(self, mock_filter):
        self.authenticate_user()
        mock_filter.return_value = {'returned_customer': True}
        response = self.client.post(self.url, self.valid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_filter.assert_called_once_with(127)

    @patch('commerce_coordinator.apps.lms.views.UserRetirementRequested.run_filter')
    def test_post_with_valid_data_invalid_pipeline_return_fails(self, mock_filter):
        self.authenticate_user()
        mock_filter.return_value = {'returned_customer': None}
        response = self.client.post(self.url, self.valid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_filter.assert_called_once_with(127)

    def test_post_with_invalid_data_fails(self):
        self.authenticate_user()
        response = self.client.post(self.url, self.invalid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('commerce_coordinator.apps.lms.views.UserRetirementRequested.run_filter')
    def test_post_with_filter_exception_fails(self, mock_filter):
        self.authenticate_user()
        mock_filter.side_effect = OpenEdxFilterException('Filter failed')
        response = self.client.post(self.url, self.valid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    @patch('commerce_coordinator.apps.lms.views.UserRetirementRequested.run_filter')
    def test_post_with_unexpected_exception_fails(self, mock_filter):
        self.authenticate_user()
        mock_filter.side_effect = Exception('Unexpected error')
        response = self.client.post(self.url, self.valid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
