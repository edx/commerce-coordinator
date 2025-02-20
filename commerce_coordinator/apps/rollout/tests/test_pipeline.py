from unittest import TestCase
from unittest.mock import patch, MagicMock
from requests import HTTPError

from openedx_filters.exceptions import OpenEdxFilterException

from commerce_coordinator.apps.commercetools_frontend.constants import COMMERCETOOLS_FRONTEND
from commerce_coordinator.apps.rollout.pipeline import (
    GetActiveOrderManagementSystem,
    ACTIVE_ORDER_MANAGEMENT_SYSTEM_KEY
)
from commerce_coordinator.apps.frontend_app_payment.constants import FRONTEND_APP_PAYMENT_CHECKOUT


class TestGetActiveOrderManagementSystem(TestCase):

    @patch('commerce_coordinator.apps.rollout.pipeline.is_user_enterprise_learner')
    def test_run_filter_with_enterprise_learner(self, mock_is_user_enterprise_learner):
        mock_is_user_enterprise_learner.return_value = True

        request = MagicMock()
        request.query_params.getlist.return_value = []
        request.query_params.get.return_value = ''

        step = GetActiveOrderManagementSystem(filter_type='test_filter_type', running_pipeline='test_running_pipeline')
        result = step.run_filter(request)

        self.assertEqual(result[ACTIVE_ORDER_MANAGEMENT_SYSTEM_KEY], FRONTEND_APP_PAYMENT_CHECKOUT)

    @patch('commerce_coordinator.apps.rollout.pipeline.is_user_enterprise_learner')
    @patch('commerce_coordinator.apps.rollout.pipeline.is_program_redirection_to_ct_enabled')
    @patch('commerce_coordinator.apps.rollout.pipeline.CommercetoolsAPIClient')
    def test_run_filter_with_bundle(self, MockCommercetoolsAPIClient, mock_is_program_redirection_to_ct_enabled,
                                    mock_is_user_enterprise_learner):
        mock_is_user_enterprise_learner.return_value = False
        mock_is_program_redirection_to_ct_enabled.return_value = True
        mock_client = MockCommercetoolsAPIClient.return_value
        mock_client.get_product_by_program_id.return_value = MagicMock()

        request = MagicMock()
        request.query_params.getlist.return_value = []
        request.query_params.get.side_effect = lambda key, default='': 'bundle_id' if key == 'bundle' else ''

        step = GetActiveOrderManagementSystem(filter_type='test_filter_type', running_pipeline='test_running_pipeline')
        result = step.run_filter(request)

        self.assertEqual(result[ACTIVE_ORDER_MANAGEMENT_SYSTEM_KEY], COMMERCETOOLS_FRONTEND)
        mock_client.get_product_by_program_id.assert_called_once_with('bundle_id')

    @patch('commerce_coordinator.apps.rollout.pipeline.is_user_enterprise_learner')
    @patch('commerce_coordinator.apps.rollout.pipeline.is_program_redirection_to_ct_enabled')
    @patch('commerce_coordinator.apps.rollout.pipeline.CommercetoolsAPIClient')
    def test_run_filter_with_bundle_flag_disabled(self, MockCommercetoolsAPIClient,
                                                  mock_is_program_redirection_to_ct_enabled,
                                                  mock_is_user_enterprise_learner):
        mock_is_user_enterprise_learner.return_value = False
        mock_is_program_redirection_to_ct_enabled.return_value = False

        request = MagicMock()
        request.query_params.getlist.return_value = []
        request.query_params.get.side_effect = lambda key, default='': 'bundle_id' if key == 'bundle' else ''

        step = GetActiveOrderManagementSystem(filter_type='test_filter_type', running_pipeline='test_running_pipeline')
        result = step.run_filter(request)

        self.assertEqual(result[ACTIVE_ORDER_MANAGEMENT_SYSTEM_KEY], FRONTEND_APP_PAYMENT_CHECKOUT)

    @patch('commerce_coordinator.apps.rollout.pipeline.is_user_enterprise_learner')
    @patch('commerce_coordinator.apps.rollout.pipeline.is_program_redirection_to_ct_enabled')
    @patch('commerce_coordinator.apps.rollout.pipeline.CommercetoolsAPIClient')
    def test_run_filter_with_no_program_found(self, MockCommercetoolsAPIClient,
                                              mock_is_program_redirection_to_ct_enabled,
                                              mock_is_user_enterprise_learner):
        mock_is_user_enterprise_learner.return_value = False
        mock_is_program_redirection_to_ct_enabled.return_value = True

        mock_client = MockCommercetoolsAPIClient.return_value
        mock_client.get_product_by_program_id.return_value = None

        request = MagicMock()
        request.query_params.getlist.return_value = []
        request.query_params.get.side_effect = lambda key, default='': 'bundle_id' if key == 'bundle' else ''

        step = GetActiveOrderManagementSystem(filter_type='test_filter_type', running_pipeline='test_running_pipeline')

        with self.assertLogs('commerce_coordinator.apps.rollout.pipeline', level='WARNING') as log:
            result = step.run_filter(request)
            self.assertEqual(result[ACTIVE_ORDER_MANAGEMENT_SYSTEM_KEY], FRONTEND_APP_PAYMENT_CHECKOUT)
            self.assertIn('[get_product_by_program_id] Program bundle_id not found in Commercetools. '
                          'Please ensure it is properly synced.', log.output[0])

    @patch('commerce_coordinator.apps.rollout.pipeline.is_user_enterprise_learner')
    @patch('commerce_coordinator.apps.rollout.pipeline.is_program_redirection_to_ct_enabled')
    @patch('commerce_coordinator.apps.rollout.pipeline.CommercetoolsAPIClient')
    def test_run_filter_with_ct_api_exception_for_bundle(self, MockCommercetoolsAPIClient,
                                                         mock_is_program_redirection_to_ct_enabled,
                                                         mock_is_user_enterprise_learner):
        mock_is_user_enterprise_learner.return_value = False
        mock_is_program_redirection_to_ct_enabled.return_value = True
        mock_client = MockCommercetoolsAPIClient.return_value
        mock_client.get_product_by_program_id.side_effect = HTTPError("API error")

        request = MagicMock()
        request.query_params.getlist.return_value = []
        request.query_params.get.side_effect = lambda key, default='': 'bundle_id' if key == 'bundle' else ''

        step = GetActiveOrderManagementSystem(filter_type='test_filter_type', running_pipeline='test_running_pipeline')

        with self.assertLogs('commerce_coordinator.apps.rollout.pipeline', level='ERROR') as log:
            result = step.run_filter(request)
            self.assertEqual(result[ACTIVE_ORDER_MANAGEMENT_SYSTEM_KEY], FRONTEND_APP_PAYMENT_CHECKOUT)
            self.assertIn("[get_product_by_program_id] Failed to get CT program", log.output[0])

    @patch('commerce_coordinator.apps.rollout.pipeline.is_user_enterprise_learner')
    @patch('commerce_coordinator.apps.rollout.pipeline.is_redirect_to_commercetools_enabled_for_user')
    @patch('commerce_coordinator.apps.rollout.pipeline.CommercetoolsAPIClient')
    def test_run_filter_with_course_run(self, MockCommercetoolsAPIClient,
                                        mock_is_redirect_to_commercetools_enabled_for_user,
                                        mock_is_user_enterprise_learner):
        mock_is_user_enterprise_learner.return_value = False
        mock_is_redirect_to_commercetools_enabled_for_user.return_value = True
        mock_client = MockCommercetoolsAPIClient.return_value
        mock_client.get_product_variant_by_course_run.return_value = MagicMock()

        request = MagicMock()
        request.query_params.getlist.return_value = ['sku1', 'sku2']
        request.query_params.get.side_effect = lambda key, default='': (
            'course_run_id' if key == 'course_run_key' else ''
        )

        step = GetActiveOrderManagementSystem(filter_type='test_filter_type', running_pipeline='test_running_pipeline')
        result = step.run_filter(request)

        self.assertEqual(result[ACTIVE_ORDER_MANAGEMENT_SYSTEM_KEY], COMMERCETOOLS_FRONTEND)
        mock_client.get_product_variant_by_course_run.assert_called_once_with('course_run_id')

    @patch('commerce_coordinator.apps.rollout.pipeline.is_user_enterprise_learner')
    @patch('commerce_coordinator.apps.rollout.pipeline.is_redirect_to_commercetools_enabled_for_user')
    @patch('commerce_coordinator.apps.rollout.pipeline.CommercetoolsAPIClient')
    def test_run_filter_with_course_run_flag_disabled(self, MockCommercetoolsAPIClient,
                                                      mock_is_redirect_to_commercetools_enabled_for_user,
                                                      mock_is_user_enterprise_learner):
        mock_is_user_enterprise_learner.return_value = False
        mock_is_redirect_to_commercetools_enabled_for_user.return_value = False

        request = MagicMock()
        request.query_params.getlist.return_value = ['sku1', 'sku2']
        request.query_params.get.side_effect = lambda key, default='': (
            'course_run_id' if key == 'course_run_key' else ''
        )

        step = GetActiveOrderManagementSystem(filter_type='test_filter_type', running_pipeline='test_running_pipeline')
        result = step.run_filter(request)

        self.assertEqual(result[ACTIVE_ORDER_MANAGEMENT_SYSTEM_KEY], FRONTEND_APP_PAYMENT_CHECKOUT)

    @patch('commerce_coordinator.apps.rollout.pipeline.is_user_enterprise_learner')
    @patch('commerce_coordinator.apps.rollout.pipeline.is_redirect_to_commercetools_enabled_for_user')
    @patch('commerce_coordinator.apps.rollout.pipeline.is_program_redirection_to_ct_enabled')
    @patch('commerce_coordinator.apps.rollout.pipeline.CommercetoolsAPIClient')
    def test_run_filter_with_no_course_found(self, MockCommercetoolsAPIClient,
                                             mock_is_program_redirection_to_ct_enabled,
                                             mock_is_redirect_to_commercetools_enabled_for_user,
                                             mock_is_user_enterprise_learner):
        mock_is_user_enterprise_learner.return_value = False
        mock_is_redirect_to_commercetools_enabled_for_user.return_value = True
        mock_is_program_redirection_to_ct_enabled.return_value = False

        mock_client = MockCommercetoolsAPIClient.return_value
        mock_client.get_product_variant_by_course_run.return_value = None

        request = MagicMock()
        request.query_params.getlist.return_value = []
        request.query_params.get.side_effect = lambda key, default='': 'bundle_id' if key == 'bundle' else ''

        step = GetActiveOrderManagementSystem(filter_type='test_filter_type', running_pipeline='test_running_pipeline')
        result = step.run_filter(request)

        self.assertEqual(result[ACTIVE_ORDER_MANAGEMENT_SYSTEM_KEY], FRONTEND_APP_PAYMENT_CHECKOUT)

    @patch('commerce_coordinator.apps.rollout.pipeline.is_user_enterprise_learner')
    @patch('commerce_coordinator.apps.rollout.pipeline.is_redirect_to_commercetools_enabled_for_user')
    @patch('commerce_coordinator.apps.rollout.pipeline.CommercetoolsAPIClient')
    def test_run_filter_with_ct_api_exception_for_course_run(self, MockCommercetoolsAPIClient,
                                                             mock_is_redirect_to_commercetools_enabled_for_user,
                                                             mock_is_user_enterprise_learner):
        mock_is_user_enterprise_learner.return_value = False
        mock_is_redirect_to_commercetools_enabled_for_user.return_value = True
        mock_client = MockCommercetoolsAPIClient.return_value
        mock_client.get_product_variant_by_course_run.side_effect = HTTPError("API error")

        request = MagicMock()
        request.query_params.getlist.return_value = ['sku1', 'sku2']
        request.query_params.get.side_effect = lambda key, default='': (
            'course_run_id' if key == 'course_run_key' else ''
        )

        step = GetActiveOrderManagementSystem(filter_type='test_filter_type', running_pipeline='test_running_pipeline')

        with self.assertLogs('commerce_coordinator.apps.rollout.pipeline', level='ERROR') as log:
            result = step.run_filter(request)
            self.assertEqual(result[ACTIVE_ORDER_MANAGEMENT_SYSTEM_KEY], FRONTEND_APP_PAYMENT_CHECKOUT)
            self.assertIn("[get_product_variant_by_course_run] Failed to get CT course", log.output[0])

    @patch('commerce_coordinator.apps.rollout.pipeline.is_user_enterprise_learner')
    @patch('commerce_coordinator.apps.rollout.pipeline.CommercetoolsAPIClient')
    def test_run_filter_with_no_params(self, MockCommercetoolsAPIClient, mock_is_user_enterprise_learner):
        mock_is_user_enterprise_learner.return_value = False

        request = MagicMock()
        request.query_params.getlist.return_value = []
        request.query_params.get.return_value = ''

        step = GetActiveOrderManagementSystem(filter_type='test_filter_type', running_pipeline='test_running_pipeline')

        with self.assertRaises(OpenEdxFilterException) as context:
            step.run_filter(request)

        self.assertIn("Unable to determine active order management system", str(context.exception))
