""" frontend_app_payment filter Tests"""

from unittest import TestCase
from unittest.mock import patch

from django.test import override_settings

from commerce_coordinator.apps.frontend_app_payment.filters import DraftPaymentRequested


class TestDraftPaymentRequestedFilter(TestCase):
    """ A pytest Test Case for then `DraftPaymentRequested` """

    @override_settings(
        OPEN_EDX_FILTERS_CONFIG={
            "org.edx.coordinator.frontend_app_payment.payment.draft.requested.v1": {
                "fail_silently": False,
                "pipeline": [
                    'commerce_coordinator.apps.titan.pipeline.GetTitanPayment',
                ]
            },
        },
    )
    @patch('commerce_coordinator.apps.titan.clients.TitanAPIClient.get_payment')
    def test_filter_when_payment_exist_in_titan(self, mock_get_payment):
        """
        Test when Payment exists in Titan system.
        """

        mock_get_payment_data = {
            'orderUuid': 'test-uuid',
            'number': '123456',
        }
        mock_get_payment.return_value = mock_get_payment_data

        filter_params = {
            'edx_lms_user_id': 1,
        }

        payment_details = DraftPaymentRequested.run_filter(filter_params)

        expected_payment_details = dict(filter_params, **mock_get_payment_data)
        self.assertEqual(expected_payment_details, payment_details)
