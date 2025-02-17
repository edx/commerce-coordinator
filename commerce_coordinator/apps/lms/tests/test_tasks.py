"""
LMS app Task Tests
"""

import logging
from unittest.mock import Mock, patch, sentinel

from django.test import TestCase
from requests import RequestException

from commerce_coordinator.apps.commercetools.catalog_info.constants import TwoUKeys
from commerce_coordinator.apps.commercetools.constants import CT_ORDER_PRODUCT_TYPE_FOR_BRAZE
from commerce_coordinator.apps.commercetools.tests.conftest import gen_line_item_state, gen_order
from commerce_coordinator.apps.core.models import User
from commerce_coordinator.apps.lms.tasks import fulfill_order_placed_send_enroll_in_course_task
from commerce_coordinator.apps.lms.tests.constants import (
    EXAMPLE_FULFILLMENT_LOGGING_OBJ,
    EXAMPLE_FULFILLMENT_REQUEST_PAYLOAD,
    EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD,
    EXAMPLE_LINE_ITEM_STATE_PAYLOAD
)

# Log using module name.
logger = logging.getLogger(__name__)

# Define unit under test.
# Note: if the UUT is part of the class as an ivar, it trims off arg0 as 'self' and
#       claims too many args supplied
uut = fulfill_order_placed_send_enroll_in_course_task


@patch('commerce_coordinator.apps.lms.tasks.LMSAPIClient')
class FulfillOrderPlacedSendEnrollInCourseTaskTest(TestCase):
    """ Fulfill Order Placed Send Enroll In Course Task Test """

    @staticmethod
    def unpack_for_uut(values):
        """ Unpack the dictionary in the order required for the UUT """
        return (
            values['course_id'],
            values['course_mode'],
            values['date_placed'],
            values['edx_lms_user_id'],
            values['email_opt_in'],
            values['order_number'],
            values['order_id'],
            values['order_version'],
            values['provider_id'],
            values['source_system'],
            values['line_item_id'],
            values['item_quantity'],
            values['line_item_state_id'],
            values['message_id'],
            values['user_first_name'],
            values['user_email'],
            values['course_title'],
            values['product_type']
        )

    def setUp(self):
        User.objects.create(username='test-user', lms_user_id=4)

    def test_correct_arguments_passed(self, mock_client):
        '''
        Check calling uut with mock_parameters yields call to client with
        expected_data.
        '''
        _ = uut(*self.unpack_for_uut(EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD))  # pylint: disable = no-value-for-parameter
        logger.info('mock_client().mock_calls: %s', mock_client().mock_calls)
        mock_client().enroll_user_in_course.assert_called_once_with(
            EXAMPLE_FULFILLMENT_REQUEST_PAYLOAD,
            EXAMPLE_LINE_ITEM_STATE_PAYLOAD,
            EXAMPLE_FULFILLMENT_LOGGING_OBJ
        )

    def test_correct_arguments_passed_credit(self, mock_client):
        '''
        Check calling uut with mock_parameters for a CREDIT course yields call
        to client with expected_data.
        '''
        # Change course_mode to credit:
        credit_mock_parameters = EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD.copy()
        credit_mock_parameters['course_mode'] = 'credit'
        credit_mock_parameters['provider_id'] = 'test-provider'

        # Add credit enrollment_attribute:
        credit_expected_data = EXAMPLE_FULFILLMENT_REQUEST_PAYLOAD.copy()
        credit_expected_data['mode'] = 'credit'
        credit_expected_data['enrollment_attributes'].append({
            'namespace': 'credit',
            'name': 'provider_id',
            'value': 'test-provider',
        })

        # Run test:
        _ = uut(*self.unpack_for_uut(credit_mock_parameters))  # pylint: disable = no-value-for-parameter
        logger.info('mock_client().mock_calls: %s', mock_client().mock_calls)
        mock_client().enroll_user_in_course.assert_called_once_with(
            credit_expected_data,
            EXAMPLE_LINE_ITEM_STATE_PAYLOAD,
            EXAMPLE_FULFILLMENT_LOGGING_OBJ
        )

    def test_passes_through_client_return(self, mock_client):
        '''
        Check uut returns whatever the client returns.
        '''
        mock_client().enroll_user_in_course.return_value = sentinel.mock_client_return_value
        res = uut(*self.unpack_for_uut(EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD))  # pylint: disable=no-value-for-parameter
        logger.info('result: %s', res)
        self.assertEqual(res, sentinel.mock_client_return_value)

    @patch('commerce_coordinator.apps.lms.tasks.CommercetoolsAPIClient.get_state_by_key')
    @patch('commerce_coordinator.apps.lms.tasks.CommercetoolsAPIClient.get_order_by_id')
    def test_retry_logic(self, mock_ct_get_order, mock_ct_get_state, mock_client):
        """
        Check if the retry logic updates the line item state ID and order version correctly.
        """
        mock_ct_get_state.return_value = gen_line_item_state()
        mock_ct_get_order.return_value = gen_order('mock_order_id')

        retry_payload = EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD.copy()
        retry_payload['line_item_state_id'] = 'initial-state-id'
        retry_payload['order_version'] = 1

        mock_client().enroll_user_in_course.side_effect = RequestException()
        uut.apply(
            args=self.unpack_for_uut(retry_payload),
            throw=False
        )

        expected_state_payload = EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD.copy()
        expected_state_payload['line_item_state_id'] = '2u-fulfillment-failure-state'
        expected_state_payload['order_version'] = 2

        mock_ct_get_state.assert_called_with(TwoUKeys.FAILURE_FULFILMENT_STATE)
        mock_ct_get_order.assert_called_with(EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD.get('order_id'))

    @patch('commerce_coordinator.apps.lms.tasks.send_unsupported_mode_fulfillment_error_email')
    @patch.object(fulfill_order_placed_send_enroll_in_course_task, 'max_retries', 5)
    def test_fulfillment_error_email_is_sent_on_failure(
            self, mock_send_email, mock_client
    ):    # pylint: disable=unused-argument
        """
        Test that `on_failure` sends the appropriate failure email.
        """
        mock_response = Mock()
        mock_response.text = '{"message": "course mode is expired or otherwise unavailable for course run"}'
        exception = RequestException("400 Bad Request")
        exception.response = mock_response

        exc = exception
        task_id = "test_task_id"
        args = []
        kwargs = EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD
        einfo = Mock()

        fulfill_order_placed_send_enroll_in_course_task.push_request(retries=5)
        fulfill_order_placed_send_enroll_in_course_task.on_failure(
            exc=exc,
            task_id=task_id,
            args=args,
            kwargs=kwargs,
            einfo=einfo
        )

        braze_product_type = CT_ORDER_PRODUCT_TYPE_FOR_BRAZE.get(
            EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD['product_type'], 'course'
        )

        mock_send_email.assert_called_once_with(
            EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD['edx_lms_user_id'],
            EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD['user_email'],
            {
                'order_number': EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD['order_number'],
                'product_type': braze_product_type,
                'product_name': EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD['course_title'],
                'first_name': EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD['user_first_name'],
            }
        )
