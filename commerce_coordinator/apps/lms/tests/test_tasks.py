"""
LMS app Task Tests
"""

import logging
from unittest.mock import patch, sentinel

from django.test import TestCase

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
            values['message_id']
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
