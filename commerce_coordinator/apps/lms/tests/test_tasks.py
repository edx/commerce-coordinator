import logging
from unittest.mock import patch, sentinel

from django.test import TestCase, override_settings

from commerce_coordinator.apps.core.models import User
from commerce_coordinator.apps.core.tests.utils import CoordinatorSignalReceiverTestCase
from commerce_coordinator.apps.lms.tasks import fulfill_order_placed_send_enroll_in_course_task
from commerce_coordinator.apps.lms.tests.constants import (
    EXAMPLE_FULFILLMENT_REQUEST_PAYLOAD,
    EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD
)

# Log using module name.
logger = logging.getLogger(__name__)


@patch('commerce_coordinator.apps.lms.tasks.LMSAPIClient')
class FulfillOrderPlacedSendEnrollInCourseTaskTest(TestCase):

    # Define unit under test.
    uut = fulfill_order_placed_send_enroll_in_course_task

    def setUp(self):
        User.objects.create(username='test-user', lms_user_id=4)

    def test_correct_arguments_passed(self, mock_client):
        '''
        Check calling uut with mock_parameters yields call to client with
        expected_data.
        '''
        result = self.uut(**EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD)
        logger.info('mock_client().mock_calls: %s', mock_client().mock_calls)
        mock_client().enroll_user_in_course.assert_called_once_with(EXAMPLE_FULFILLMENT_REQUEST_PAYLOAD)

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
        result = self.uut(**credit_mock_parameters)
        logger.info('mock_client().mock_calls: %s', mock_client().mock_calls)
        mock_client().enroll_user_in_course.assert_called_once_with(credit_expected_data)

    def test_passes_through_client_return(self, mock_client):
        '''
        Check uut returns whatever client returns.
        '''
        mock_client().enroll_user_in_course.return_value = sentinel.mock_client_return_value
        result = self.uut(**EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD)
        logger.info('result: %s', result)
        self.assertEqual(result, sentinel.mock_client_return_value)
