"""
Tests for the LMS (edx-platform) views.
"""
import copy
from unittest import mock
from urllib.parse import unquote

import ddt
import requests_mock
from commercetools.exceptions import CommercetoolsError
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from mock import patch
from openedx_filters.exceptions import OpenEdxFilterException
from requests import HTTPError
from rest_framework import status
from rest_framework.test import APITestCase

from commerce_coordinator.apps.commercetools.tests.conftest import (
    APITestingSet,
    gen_program_search_result,
    gen_variant_search_result
)
from commerce_coordinator.apps.core.exceptions import InvalidFilterType
from commerce_coordinator.apps.core.tests.utils import name_test
from commerce_coordinator.apps.lms.constants import DEFAULT_BUNDLE_DISCOUNT_KEY

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
    def test_run_rollout_pipeline_redirect_to_commercetools_course(self, is_redirect_mock):
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

    @patch('commerce_coordinator.apps.rollout.pipeline.is_program_redirection_to_ct_enabled')
    def test_run_rollout_pipeline_redirect_to_commercetools_program(self, is_redirect_mock):
        base_url = self.client_set.get_base_url_from_client()
        self.client.login(username=self.test_user_username, password=self.test_user_password)
        # Because the base mocker can't do param binding, we have to intercept.
        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.get(
                f"{base_url}product-projections/search?filter=key%3A%22818aff6f-1a39-4515-8779-dfebc0742d8e%22",
                json=gen_program_search_result().serialize()
            )

            ret_program = self.client_set.client.get_product_by_program_id(
                '818aff6f-1a39-4515-8779-dfebc0742d8e'
            )
            is_redirect_mock.return_value = True
            self.client.force_authenticate(user=self.user)
            response = self.client.get(
                self.url,
                {'sku': ['sku1', 'sku2'], 'bundle': '818aff6f-1a39-4515-8779-dfebc0742d8e'}
            )
            self.assertTrue(response.url.startswith(settings.COMMERCETOOLS_FRONTEND_URL))
            self.assertIn(ret_program.key, unquote(unquote(response.url)))

    @ddt.unpack
    @patch('commerce_coordinator.apps.rollout.pipeline.is_redirect_to_commercetools_enabled_for_user')
    def test_payment_page_redirect_program(self, is_redirect_mock):
        base_url = self.client_set.get_base_url_from_client()
        self.client.login(username=self.test_user_username, password=self.test_user_password)
        # Because the base mocker can't do param binding, we have to intercept.
        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.get(
                f"{base_url}product-projections/search?filter=key%3A%22818aff6f-1a39-4515-8779-dfebc0742d8e%22",
                json=gen_program_search_result().serialize()
            )

            is_redirect_mock.return_value = True
            self.client.login(username=self.test_user_username, password=self.test_user_password)
            self.client.force_authenticate(user=self.user)
            response = self.client.get(
                self.url,
                {'sku': ['sku1', 'sku2'], 'bundle': '818aff6f-1a39-4515-8779-dfebc0742d8e'}
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

    entitlement_valid_payload = {
        'username': 'testuser',
        'order_number': 'ORDER123',
        'entitlement_uuid': 'ENTITLEMENT123'
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
    def test_post_with_filter_exception_already_exist(self, mock_filter):
        self.authenticate_user()
        mock_filter.side_effect = InvalidFilterType('Refund already created')
        response = self.client.post(self.url, self.valid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

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

    @patch('commerce_coordinator.apps.lms.views.get_order_line_item_info_from_entitlement_uuid')
    @patch('commerce_coordinator.apps.lms.views.OrderRefundRequested.run_filter')
    def test_refund_entitlement_success(self, mock_run_filter, mock_get_line_item):
        mock_run_filter.return_value = {'returned_order': True}
        mock_get_line_item.return_value = ('order_id', 'line_item_id')
        self.authenticate_user()
        response = self.client.post(self.url, self.entitlement_valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('commerce_coordinator.apps.lms.views.get_order_line_item_info_from_entitlement_uuid')
    @patch('commerce_coordinator.apps.lms.views.OrderRefundRequested.run_filter')
    def test_refund_entitlement_failure(self, mock_run_filter, mock_get_line_item):
        mock_run_filter.return_value = {'returned_order': None}
        mock_get_line_item.return_value = ('order_id', 'line_item_id')
        self.authenticate_user()
        response = self.client.post(self.url, self.entitlement_valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('commerce_coordinator.apps.lms.views.get_order_line_item_info_from_entitlement_uuid')
    def test_refund_entitlement_commercetools_error(self, mock_get_line_item):
        mock_get_line_item.side_effect = CommercetoolsError(
            message="Could not create return transaction",
            errors="Some error message",
            response={}
        )
        self.authenticate_user()
        response = self.client.post(self.url, self.entitlement_valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    @patch('commerce_coordinator.apps.lms.views.OrderRefundRequested.run_filter')
    def test_post_with_invalid_entitlement_data_fails(self, mock_filter):
        self.authenticate_user()
        invalid_payload = copy.deepcopy(self.entitlement_valid_payload)
        invalid_payload['entitlement_uuid'] = ''
        response = self.client.post(self.url, invalid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_filter.assert_not_called()


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

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        mock_filter.assert_called_once_with(127)

    @patch('commerce_coordinator.apps.lms.views.UserRetirementRequested.run_filter')
    def test_post_with_valid_data_invalid_pipeline_return_fails(self, mock_filter):
        self.authenticate_user()
        mock_filter.return_value = {'returned_customer': None}
        response = self.client.post(self.url, self.valid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_filter.assert_called_once_with(127)

    @patch('commerce_coordinator.apps.lms.views.UserRetirementRequested.run_filter')
    def test_post_with_valid_data_pipeline_return_customer_not_found(self, mock_filter):
        self.authenticate_user()
        mock_filter.return_value = {'returned_customer': 'customer_not_found'}
        response = self.client.post(self.url, self.valid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
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


@ddt.ddt
class FirstTimeDiscountEligibleViewTests(APITestCase):
    """
    Tests for the FirstTimeDiscountEligibleView to check if a user is eligible for a first-time discount.
    """

    test_user_username = 'test'
    test_user_email = 'test@example.com'
    test_user_password = 'secret'
    test_discount = 'first_time_discount'

    valid_payload = {
        'email': test_user_email,
        'code': test_discount,
    }

    invalid_payload = {
        'email': None,
        'code': 'any_discount',
    }

    url = reverse('lms:first_time_discount_eligible')

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

    @patch(
        'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient'
        '.is_first_time_discount_eligible'
    )
    def test_get_with_valid_email_eligibility_true(self, mock_is_first_time_discount_eligible):
        """
        Test case where the user is eligible for a first-time discount.
        """
        self.authenticate_user()
        mock_is_first_time_discount_eligible.return_value = True

        response = self.client.post(self.url, self.valid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"is_eligible": True})
        mock_is_first_time_discount_eligible.assert_called_once_with(self.test_user_email, self.test_discount)

    @patch(
        'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient'
        '.is_first_time_discount_eligible'
    )
    def test_get_with_valid_email_eligibility_false(self, mock_is_first_time_discount_eligible):
        """
        Test case where the user is not eligible for a first-time discount.
        """
        self.authenticate_user()
        mock_is_first_time_discount_eligible.return_value = False

        response = self.client.post(self.url, self.valid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"is_eligible": False})
        mock_is_first_time_discount_eligible.assert_called_once_with(self.test_user_email, self.test_discount)

    def test_get_with_missing_email_fails(self):
        """
        Test case where the email is not provided in the request query params.
        """
        self.authenticate_user()

        response = self.client.post(self.url, self.invalid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ProgramPriceViewTests(APITestCase):
    """Tests for ProgramPriceView."""

    test_user_username = 'test'
    test_user_email = 'test@example.com'
    test_user_password = 'secret'

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            self.test_user_username,
            self.test_user_email,
            self.test_user_password,
        )
        self.url = reverse("lms:program_price_info", kwargs={"bundle_key": "test-bundle-key"})
        self.mock_ct_api_client = mock.patch('commerce_coordinator.apps.lms.views.CTCustomAPIClient').start()
        self.addCleanup(mock.patch.stopall)

    def tearDown(self):
        super().tearDown()
        self.client.logout()

    def authenticate_user(self):
        self.client.login(username=self.test_user_username, password=self.test_user_password)
        self.client.force_authenticate(user=self.user)

    def test_program_variants_not_found(self):
        """Verify 404 is returned when program variants are not found."""
        self.authenticate_user()
        self.mock_ct_api_client.return_value.get_program_variants.return_value = None

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, 'Program variants not found.')

    def test_program_price_calculation_with_offer(self):
        """Verify the program price is calculated correctly with program offer."""
        self.authenticate_user()
        self.mock_ct_api_client.return_value.get_program_variants.return_value = [
            {'variant_key': 'ai+edX+DemoX', 'entitlement_sku': 'uuid16'},
            {'variant_key': 'ai+edX+M12', 'entitlement_sku': 'uuid16'}
        ]
        self.mock_ct_api_client.return_value.get_ct_bundle_offers_without_code.return_value = [
            {
                "key": DEFAULT_BUNDLE_DISCOUNT_KEY,
                "value": {"type": "relative", "permyriad": 1000},
                "target": {
                    "predicate": "custom.bundleId is defined and (custom.bundleId = 'test-bundle-key')"
                }
            }
        ]
        self.mock_ct_api_client.return_value.get_standalone_prices_for_skus.return_value = [
            {'value': {'centAmount': 2000, 'currencyCode': 'USD'}},
            {'value': {'centAmount': 1000, 'currencyCode': 'USD'}}
        ]

        response = self.client.get(self.url, {'username': 'test_user', 'course_key': ['edX+DemoX', 'edX+M12']})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {
            "total_incl_tax_excl_discounts": 30.0,
            "total_incl_tax": 27.0,
            "currency": "USD"
        })

    def test_program_price_calculation_without_offer(self):
        """Verify the program price is calculated correctly without program offer."""
        self.authenticate_user()
        self.mock_ct_api_client.return_value.get_program_variants.return_value = [
            {'variant_key': 'ai+edX+DemoX', 'entitlement_sku': 'uuid16'},
            {'variant_key': 'ai+edX+M12', 'entitlement_sku': 'uuid16'}
        ]
        self.mock_ct_api_client.return_value.get_ct_bundle_offers_without_code.return_value = []
        self.mock_ct_api_client.return_value.get_standalone_prices_for_skus.return_value = [
            {'value': {'centAmount': 2000, 'currencyCode': 'USD'}},
            {'value': {'centAmount': 1000, 'currencyCode': 'USD'}}
        ]

        response = self.client.get(self.url, {'username': 'test_user', 'course_key': ['edX+DemoX', 'edX+M12']})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {
            "total_incl_tax_excl_discounts": 30.0,
            "total_incl_tax": 30.0,
            "currency": "USD"
        })

    def test_CT_http_error_handling(self):
        """Verify HTTP 500 is returned when an HTTPError occurs."""
        self.authenticate_user()
        self.mock_ct_api_client.return_value.get_program_variants.side_effect = HTTPError("HTTP Error")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data, 'Error occurred while fetching data')
