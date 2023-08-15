"""
Tests for the LMS (edx-platform) views.
"""
import uuid
from urllib.parse import parse_qs, urlparse

import ddt
import django.conf
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from mock import patch
from openedx_filters import PipelineStep
from rest_framework import status
from rest_framework.test import APITestCase

from commerce_coordinator.apps.core.constants import QueryParamPrefixes, WaffleFlagNames
from commerce_coordinator.apps.core.tests.utils import name_test
from commerce_coordinator.apps.lms.filters import OrderCreateRequested

User = get_user_model()


class TestOrderCreateRequestedFilterPipelineThatExplodes(PipelineStep):
    """
    An example exploding Pipeline, to test filter failures return expected codes when if something is uncaught
    """

    targets = 'org.edx.coordinator.lms.order.create.requested.v1'

    @classmethod
    def get_fqtn(cls):
        """ Return the fully qualified type name to this class """
        return f'{cls.__module__}.{cls.__qualname__}'

    def run_filter(self, params, order_data):  # pylint: disable=arguments-differ
        """ Implemented by the default pipeline, this intentionally explodes on us. Has a bomb emoji too. """
        raise Exception('\U0001f4a3 (this is intentional)')


class TestOrderCreateRequestedFilterPipelineRecordsInputData(PipelineStep):
    """
    An example no-op Pipeline, to test filter success and validate result
    """

    LAST_DATA = None
    targets = 'org.edx.coordinator.lms.order.create.requested.v1'

    @classmethod
    def get_fqtn(cls):
        """ Return the fully qualified type name to this class """
        return f'{cls.__module__}.{cls.__qualname__}'

    def run_filter(self, params, order_data):  # pylint: disable=arguments-differ
        """ Implemented by the default pipeline, this intentionally doesnt do much, but allows introspection. """
        TestOrderCreateRequestedFilterPipelineRecordsInputData.LAST_DATA = {
            'params': dict(params),
            'order_data': order_data
        }
        return TestOrderCreateRequestedFilterPipelineRecordsInputData.LAST_DATA


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

    @override_settings(
        OPEN_EDX_FILTERS_CONFIG={
            TestOrderCreateRequestedFilterPipelineThatExplodes.targets: {
                'fail_silently': False,  # explosion won't be caught if true (the default)
                'pipeline': [
                    TestOrderCreateRequestedFilterPipelineThatExplodes.get_fqtn(),
                ],
            },
        }
    )
    def test_filter_exceptions_return_500(self):
        # Validate pipeline
        configs = OrderCreateRequested.get_pipeline_configuration()[0]
        self.assertEqual(1, len(configs))
        self.assertIn(TestOrderCreateRequestedFilterPipelineThatExplodes.get_fqtn(), configs)

        query_params = {
            'coupon_code': 'test_code', 'sku': ['sku1'],
        }

        user_email = 'pass-by-param@example.com'

        self.user = User.objects.create_user(
            self.test_user_username + str(uuid.uuid4()),  # User IDs must be Unique.
            user_email,
            self.test_user_password,
            # TODO: Remove is_staff=True
            is_staff=True,
            lms_user_id=1
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url, data=query_params)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    @override_settings(
        OPEN_EDX_FILTERS_CONFIG={
            TestOrderCreateRequestedFilterPipelineRecordsInputData.targets: {
                'fail_silently': True,  # explosion won't be caught if true (the default)
                'pipeline': [
                    TestOrderCreateRequestedFilterPipelineRecordsInputData.get_fqtn(),
                ],
            },
        }
    )
    @ddt.data(
        name_test(
            "test success with coupon",
            (
                {
                    'lms_user_id': 1, 'email': 'pass-by-param@example.com',
                },
                {
                    'coupon_code': 'test_code', 'sku': ['sku1'],
                },
                status.HTTP_303_SEE_OTHER,
                {
                    'order_data': None,
                    'params': {
                        'edx_lms_user_id': 1, 'email': 'pass-by-param@example.com',
                        'sku': ['sku1'], 'coupon_code': 'test_code',
                    }
                }
            )
        ),
        name_test(
            "test coupon optional success",
            (
                {
                    'lms_user_id': 1, 'email': 'pass-by-param@example.com',
                },
                {'sku': ['sku1']},
                status.HTTP_303_SEE_OTHER,
                {
                    'order_data': None,
                    'params': {
                        'edx_lms_user_id': 1, 'email': 'pass-by-param@example.com',
                        'sku': ['sku1'], 'coupon_code': None
                    }
                }
            )
        ),
        name_test(
            "test failure, sku must have 1 value",
            (
                {
                    'lms_user_id': 1, 'email': 'pass-by-param@example.com',
                },
                {'coupon_code': 'test_code', 'sku': []},
                status.HTTP_400_BAD_REQUEST,
                {'error_key': 'sku', 'error_message': 'This list may not be empty.'}
            )
        ),
        name_test(
            "test failure, sku must not be null",
            (
                {
                    'lms_user_id': 1, 'email': 'pass-by-param@example.com',
                },
                {'coupon_code': 'test_code'},
                status.HTTP_400_BAD_REQUEST,
                {'error_key': 'sku', 'error_message': 'This list may not be empty.'}
            )
        ),
        name_test(
            "test failure, sku must not be string",
            (
                {
                    'lms_user_id': 1, 'email': 'pass-by-param@example.com',
                },
                {'coupon_code': 'test_code', 'sku': ''},
                status.HTTP_400_BAD_REQUEST,
                {'error_key': 'sku', 'error_message': 'This field may not be blank.'}
            )
        ),
        name_test(
            "test failure, edx_lms_user_id must be set",
            (
                {
                    'email': 'pass-by-param@example.com',
                },
                {'coupon_code': 'test_code', 'sku': ['sku1']},
                status.HTTP_400_BAD_REQUEST,
                {'error_key': 'edx_lms_user_id', 'error_message': 'This field may not be null.'}
            )
        ),
        name_test(
            "test failed, email cannot be empty",
            (
                {
                    'lms_user_id': 1, 'email': '',
                },
                {
                    'coupon_code': 'test_code', 'sku': ['sku1'],
                },
                status.HTTP_400_BAD_REQUEST,
                {'error_key': 'email', 'error_message': 'This field may not be blank.'}
            )
        ),
        name_test(
            "test failed, email cannot be invalid",
            (
                {
                    'lms_user_id': 1, 'email': '#^#$%^',
                },
                {
                    'coupon_code': 'test_code', 'sku': ['sku1'],
                },
                status.HTTP_400_BAD_REQUEST,
                {'error_key': 'email', 'error_message': 'Enter a valid email address.'}
            )
        ),
    )
    @ddt.unpack
    @patch('commerce_coordinator.apps.titan.signals.order_created_save_task.delay')
    def test_create_order(
        self,
        user_params,
        in_query_params,
        expected_status,
        expected_error_or_response,
        _mock_order_created_save_task
    ):

        # Validate pipeline
        configs = OrderCreateRequested.get_pipeline_configuration()[0]
        self.assertEqual(1, len(configs))
        self.assertIn(TestOrderCreateRequestedFilterPipelineRecordsInputData.get_fqtn(), configs)

        is_redirect_test = status.HTTP_301_MOVED_PERMANENTLY <= expected_status <= status.HTTP_303_SEE_OTHER

        query_params = {**in_query_params}

        user_email = None

        if 'email' in user_params:  # positional parameters cant be sent through
            user_email = user_params['email']
            del user_params['email']

        self.user = User.objects.create_user(
            self.test_user_username + str(uuid.uuid4()),  # User IDs must be Unique.
            user_email,
            self.test_user_password,
            # TODO: Remove is_staff=True
            is_staff=True,
            **user_params
        )

        waffle_flag_get_param = f'{QueryParamPrefixes.WAFFLE_FLAG.value}{WaffleFlagNames.COORDINATOR_ENABLED.value}'

        if is_redirect_test:
            query_params.update({
                'utm_source': uuid.uuid4(),
                'utm_custom': uuid.uuid4(),
            })

        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url, data=query_params)
        self.assertEqual(response.status_code, expected_status)

        if is_redirect_test:
            redirect_location: str = response.headers['Location']

            self.assertNotEqual(None, TestOrderCreateRequestedFilterPipelineRecordsInputData.LAST_DATA)

            self.assertEqual(
                TestOrderCreateRequestedFilterPipelineRecordsInputData.LAST_DATA,
                expected_error_or_response
            )

            query_params = parse_qs(urlparse(response.headers['Location']).query)

            self.assertTrue(redirect_location.startswith(django.conf.settings.PAYMENT_MICROFRONTEND_URL))
            self.assertIn("utm_", redirect_location, "No UTM Params Found")
            self.assertIn(f"utm_source={query_params['utm_source'][0]}",
                          redirect_location, "Std UTM Params Not Found")
            self.assertIn(f"utm_custom={query_params['utm_custom'][0]}",
                          redirect_location, "Custom UTM Params Not Found")
            self.assertIn(f"{waffle_flag_get_param}={query_params[waffle_flag_get_param][0]}",
                          redirect_location, "Waffle Flag was not passed through.")
        else:
            response_json = response.json()
            expected_error_key = expected_error_or_response['error_key']
            expected_error_message = expected_error_or_response['error_message']
            self.assertIn(expected_error_key, response_json)
            self.assertIn(expected_error_message, str(response_json[expected_error_key]))
