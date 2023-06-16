""" frontend_app_payment filter Tests"""

from unittest import TestCase
from unittest.mock import patch

from django.test import override_settings

from commerce_coordinator.apps.core.constants import PaymentState
from commerce_coordinator.apps.frontend_app_payment.filters import DraftPaymentRequested
from commerce_coordinator.apps.titan.tests.test_clients import ORDER_UUID


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
    @patch('commerce_coordinator.apps.titan.pipeline.GetTitanPayment.run_filter')
    def test_filter_when_payment_exist_in_titan(self, mock_pipeline):
        """
        Test when Payment exists in Titan system.
        """

        mock_payment = {
            'payment_number': '12345',
            'order_uuid': ORDER_UUID,
            'key_id': 'test-code',
            'state': PaymentState.PROCESSING.value
        }
        mock_pipeline.return_value = mock_payment
        filter_params = {
            'edx_lms_user_id': 1,
        }
        payment_details = DraftPaymentRequested.run_filter(filter_params)
        self.assertEqual(mock_payment, payment_details)
