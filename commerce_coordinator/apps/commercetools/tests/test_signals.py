""" Test LMS App Signals """

import logging
from unittest.mock import patch

from django.test import override_settings
from copy import copy

from commerce_coordinator.apps.core.tests.utils import CoordinatorSignalReceiverTestCase

# Log using module name.
logger = logging.getLogger(__name__)


@override_settings(
    CC_SIGNALS={
        'commerce_coordinator.apps.core.tests.utils.example_signal': [
            'commerce_coordinator.apps.commercetools.signals.fulfill_order_completed_send_line_item_state',
        ],
    }
)

@patch('commerce_coordinator.apps.commercetools.signals.update_line_item_state_on_fulfillment_completion')
class FulfillOrderCompletedSendLineItemStateTest(CoordinatorSignalReceiverTestCase):
    """ LMS Fulfillment Order Placed, Line Item State Update Signal Tester"""
    mock_parameters = {
        'order_id': 1,
        'order_version': 2,
        'item_id': 3,
        'item_quantity': 1,
        'line_item_state_id': 4,
    }

    def test_correct_arguments_passed_fulfillment_true(self, mock_task):
        self.mock_parameters['is_fulfilled'] = True
        _, logs = self.fire_signal()
        self.mock_parameters.pop('is_fulfilled')
        task_mock_parameters = copy(self.mock_parameters)
        task_mock_parameters['from_state_id'] = task_mock_parameters.pop('line_item_state_id')
        logger.info('logs.output: %s', logs.output)
        mock_task.assert_called_with(**task_mock_parameters, to_state_key='2u-fulfillment-success-state')


    def test_correct_arguments_passed_fulfillment_false(self, mock_task):
        self.mock_parameters['is_fulfilled'] = False
        _, logs = self.fire_signal()
        self.mock_parameters.pop('is_fulfilled')
        task_mock_parameters = copy(self.mock_parameters)
        task_mock_parameters['from_state_id'] = task_mock_parameters.pop('line_item_state_id')
        logger.info('logs.output: %s', logs.output)
        mock_task.assert_called_with(**task_mock_parameters, to_state_key='2u-fulfillment-failure-state')
