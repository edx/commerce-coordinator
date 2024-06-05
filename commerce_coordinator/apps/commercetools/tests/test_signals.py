""" Test LMS App Signals """

import logging
from copy import copy
from unittest.mock import patch

from django.test import override_settings

from commerce_coordinator.apps.core.tests.utils import CoordinatorSignalReceiverTestCase
from commerce_coordinator.apps.commercetools.tests.constants import EXAMPLE_RETURNED_ORDER_STRIPE_SIGNAL_PAYLOAD

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
        'line_item_id': 3,
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


@override_settings(
    CC_SIGNALS={
        'commerce_coordinator.apps.core.tests.utils.example_signal': [
            'commerce_coordinator.apps.commercetools.signals.refund_from_stripe',
        ],
    }
)
@patch('commerce_coordinator.apps.commercetools.signals.refund_from_stripe_task')
class RefundFromStripeTest(CoordinatorSignalReceiverTestCase):
    """ Stripe Dashboard Refund Placed, Create Return CT Transaction Signal Tester"""
    mock_parameters = EXAMPLE_RETURNED_ORDER_STRIPE_SIGNAL_PAYLOAD

    def test_correct_arguments_passed(self, mock_task):
        _, logs = self.fire_signal()
        logger.info('logs.output: %s', logs.output)
        mock_task.delay.assert_called_once_with(
            payment_intent_id=self.mock_parameters['payment_intent_id'],
            stripe_refund=self.mock_parameters['stripe_refund']
        )

    def test_correct_response_returned(self, mock_task):
        mock_task.delay.return_value.id = 'bogus_task_id'
        result, _ = self.fire_signal()
        logger.info('result: %s', result)
        self.assertEqual(result[0][1], 'bogus_task_id',
                         'Check reciever result is same as return from task')
