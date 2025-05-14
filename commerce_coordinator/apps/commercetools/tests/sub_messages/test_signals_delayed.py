""" Commercetools Subscription Message Signals """

import logging
from unittest.mock import patch

from django.test import override_settings

from commerce_coordinator.apps.commercetools.constants import SOURCE_SYSTEM
from commerce_coordinator.apps.core.tests.utils import CoordinatorSignalReceiverTestCase, uuid4_str

# Log using module name.
logger = logging.getLogger(__name__)


@override_settings(
    CC_SIGNALS={
        'commerce_coordinator.apps.core.tests.utils.example_signal': [
            'commerce_coordinator.apps.commercetools.sub_messages.signals_delayed.fulfill_order_placed_message_signal',
        ],
    }
)
@patch('commerce_coordinator.apps.commercetools.sub_messages.signals_delayed.fulfill_order_placed_message_signal_task')
class FulfillOrderPlacedMessageSignalTest(CoordinatorSignalReceiverTestCase):
    """ Commercetools Fulfillment Order Placed Signal Tester"""
    mock_parameters = {
        'order_id': uuid4_str(),
        'line_item_state_id': uuid4_str(),
        'source_system': SOURCE_SYSTEM,
        'message_id': uuid4_str(),
        'is_order_fulfillment_forwarding_enabled': False
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
                         'Check receiver result is same as return from task')


@override_settings(
    CC_SIGNALS={
        'commerce_coordinator.apps.core.tests.utils.example_signal': [
            'commerce_coordinator.apps.commercetools.sub_messages.signals_delayed'
            '.fulfill_order_sanctioned_message_signal',
        ],
    }
)
@patch('commerce_coordinator.apps.commercetools.sub_messages.signals_delayed'
       '.fulfill_order_sanctioned_message_signal_task')
class SanctionedOrderPlacedMessageSignalTest(CoordinatorSignalReceiverTestCase):
    """ Commercetools Sanctioned Order Placed Signal Tester"""
    mock_parameters = {
        'order_id': uuid4_str(),
        'message_id': uuid4_str()
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
                         'Check receiver result is same as return from task')


@override_settings(
    CC_SIGNALS={
        'commerce_coordinator.apps.core.tests.utils.example_signal': [
            'commerce_coordinator.apps.commercetools.sub_messages.signals_delayed.fulfill_order_returned_signal',
        ],
    }
)
@patch('commerce_coordinator.apps.commercetools.sub_messages.signals_delayed.fulfill_order_returned_signal_task')
class ReturnedOrderPlacedMessageSignalTest(CoordinatorSignalReceiverTestCase):
    """ Commercetools Returned Order Placed Signal Tester"""
    mock_parameters = {
        'order_id': uuid4_str(),
        'return_items': [{
            'id': uuid4_str(),
            'lineItemId': uuid4_str()
        }],
        'message_id': uuid4_str()
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
                         'Check receiver result is same as return from task')
