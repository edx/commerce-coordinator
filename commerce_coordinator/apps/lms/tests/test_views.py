"""
Tests for the LMS (edx-platform) views.
"""
from urllib.parse import unquote

import ddt
import requests_mock
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from mock import patch
from rest_framework import status
from rest_framework.test import APITestCase

from commerce_coordinator.apps.commercetools.catalog_info.constants import EdXFieldNames
from commerce_coordinator.apps.commercetools.catalog_info.foundational_types import TwoUCustomTypes
from commercetools.platform.models import (
    Customer,
    CustomerPagedQueryResponse,
    Order,
    OrderPagedQueryResponse,
)
from commerce_coordinator.apps.commercetools.tests.conftest import (
    APITestingSet,
    gen_example_customer,
    gen_order_history,
    gen_variant_search_result
)
from commerce_coordinator.apps.core.constants import ORDER_HISTORY_PER_SYSTEM_REQ_LIMIT

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
        id_num = 127
        type_val = self.client_set.client.ensure_custom_type_exists(TwoUCustomTypes.CUSTOMER_TYPE_DRAFT)
        customer = gen_example_customer()
        orders = gen_order_history()
        customer.custom.fields[EdXFieldNames.LMS_USER_ID] = id_num

        # The Draft converter changes the ID, so let's update our customer and draft.
        customer.custom.type.id = type_val.id

        self.client_set.backend_repo.customers.add_existing(customer)

        for order in orders:
            order.customer_id = customer.id
            self.client_set.backend_repo.orders.add_existing(order)

        limit = ORDER_HISTORY_PER_SYSTEM_REQ_LIMIT

        # Because the base mocker can't do param binding, we have to intercept.
        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.get(
                f"{base_url}customers?"
                f"where=custom%28fields%28edx-lms_user_id%3D%3Aid%29%29"
                f"&limit=2"
                f"&var.id={id_num}",
                json=CustomerPagedQueryResponse(
                    limit=limit, count=1, total=1, offset=0,
                    results=self.client_set.fetch_from_storage('customer', Customer),
                ).serialize()
            )
            mocker.get(
                f"{base_url}orders?"
                f"where=customerId%3D%3Acid&"
                f"limit={limit}&"
                f"offset=0&"
                f"sort=completedAt+desc&"
                f"var.cid={customer.id}",
                json=OrderPagedQueryResponse(
                    limit=limit, count=1, total=1, offset=0,
                    results=self.client_set.fetch_from_storage('order', Order),
                ).serialize()
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


TEST_ECOMMERCE_URL = 'https://testserver.com'


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

    @patch('commerce_coordinator.apps.rollout.pipeline.is_redirect_to_commercetools_enabled_for_user')
    def test_run_rollout_pipeline_redirect_to_commercetools(self, is_redirect_mock):
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
            self.client.force_authenticate(user=self.user)
            response = self.client.get(
                self.url,
                {'sku': ['sku1'], 'course_run_key': 'course-v1:MichiganX+InjuryPreventionX+1T2021'}
            )
            self.assertTrue(response.headers['Location'].startswith(settings.COMMERCETOOLS_FRONTEND_URL))
            self.assertIn(ret_variant.sku, unquote(unquote(response.url)))

    @patch('commerce_coordinator.apps.rollout.pipeline.is_redirect_to_commercetools_enabled_for_user')
    def test_run_filter_only_sku_available(self, is_redirect_mock):
        self.client.login(username=self.test_user_username, password=self.test_user_password)
        is_redirect_mock.return_value = False
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {'sku': ['sku1']})
        self.assertTrue(response.headers['Location'].startswith(settings.ECOMMERCE_URL))

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
