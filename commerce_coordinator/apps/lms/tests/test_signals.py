import logging
from unittest.mock import patch, sentinel

from django.test import override_settings

from commerce_coordinator.apps.core.tests.utils import CoordinatorSignalReceiverTestCase
from commerce_coordinator.apps.lms.tests.constants import EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD

# Log using module name.
logger = logging.getLogger(__name__)


@override_settings(
    CC_SIGNALS={
        'commerce_coordinator.apps.core.tests.utils.example_signal': [
            'commerce_coordinator.apps.lms.signals.fulfill_order_placed_send_enroll_in_course',
        ],
    }
)
@patch('commerce_coordinator.apps.lms.signals.fulfill_order_placed_send_enroll_in_course_task')
class FulfillOrderPlacedSendEnrollInCourseTest(CoordinatorSignalReceiverTestCase):

    mock_parameters = EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD

    def test_correct_arguments_passed(self, mock_task):
        result, logs = self.fire_signal()
        logger.info('logs.output: %s', logs.output)
        mock_task.delay.assert_called_once_with(**self.mock_parameters)

    def test_correct_response_returned(self, mock_task):
        mock_task.delay.return_value.id = 'bogus_task_id'
        result, logs = self.fire_signal()
        logger.info('result: %s', result)
        self.assertEqual(result[0][1], 'bogus_task_id',
                         'Check reciever result is same as return from task')
