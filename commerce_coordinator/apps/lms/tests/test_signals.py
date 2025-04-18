""" Test LMS App Signals """

import logging
from unittest.mock import patch

from django.test import override_settings

from commerce_coordinator.apps.core.tests.utils import CoordinatorSignalReceiverTestCase

# Log using module name.
logger = logging.getLogger(__name__)


@override_settings(
    CC_SIGNALS={
        'commerce_coordinator.apps.core.tests.utils.example_signal': [
            'commerce_coordinator.apps.lms.signal_handlers.fulfill_order_placed_send_enroll_in_course',
        ],
    }
)
@patch('commerce_coordinator.apps.lms.signal_handlers.fulfill_order_placed_send_enroll_in_course_task')
class FulfillOrderPlacedSendEnrollInCourseTest(CoordinatorSignalReceiverTestCase):
    """ LMS Fulfillment Order Placed, Enrollment Signal Tester"""
    mock_parameters = {
        'course_id': 1,
        'course_mode': 2,
        'date_placed': 3,
        'edx_lms_user_id': 4,
        'email_opt_in': 5,
        'order_number': 6,
        'order_id': 7,
        'order_version': 8,
        'provider_id': 9,
        'source_system': 10,
        'line_item_id': 11,
        'item_quantity': 1,
        'line_item_state_id': 12,
        'message_id': 13,
        'user_first_name': 14,
        'user_last_name': 15,
        'user_email': 16,
        'product_title': 17,
        'product_type': 'edx_course',
    }

    def test_correct_arguments_passed(self, mock_task):
        _, logs = self.fire_signal()
        logger.info('logs.output: %s', logs.output)
        mock_task.delay.assert_called_once_with(**self.mock_parameters)

    def test_correct_response_returned(self, mock_task):
        mock_task.delay.return_value.id = 'bogus_task_id'
        result, _ = self.fire_signal()
        logger.info('result: %s', result)
        self.assertEqual(result[0][1], 'bogus_task_id',
                         'Check reciever result is same as return from task')


@override_settings(
    CC_SIGNALS={
        'commerce_coordinator.apps.core.tests.utils.example_signal': [
            'commerce_coordinator.apps.lms.signal_handlers.fulfill_order_placed_send_entitlement',
        ],
    }
)
@patch('commerce_coordinator.apps.lms.signal_handlers.fulfill_order_placed_send_entitlement_task')
class FulfillOrderPlacedSendEntitlementTest(CoordinatorSignalReceiverTestCase):
    """ LMS Fulfillment Order Placed, Entitlement Signal Tester"""
    mock_parameters = {
        'course_id': 1,
        'course_mode': 2,
        'edx_lms_user_id': 4,
        'email_opt_in': 5,
        'order_number': 6,
        'order_id': 7,
        'order_version': 8,
        'line_item_id': 11,
        'item_quantity': 1,
        'line_item_state_id': 12,
        'message_id': 13,
        'user_first_name': 14,
        'user_last_name': 15,
        'user_email': 16,
        'product_title': 17,
        'product_type': 18,
    }

    def test_correct_arguments_passed(self, mock_task):
        _, logs = self.fire_signal()
        logger.info('logs.output: %s', logs.output)
        mock_task.delay.assert_called_once_with(**self.mock_parameters)

    def test_correct_response_returned(self, mock_task):
        mock_task.delay.return_value.id = 'bogus_task_id'
        result, _ = self.fire_signal()
        logger.info('result: %s', result)
        self.assertEqual(result[0][1], 'bogus_task_id',
                         'Check reciever result is same as return from task')
