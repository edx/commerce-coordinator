""" Test Commercetools App Signals """

import logging
from copy import copy
from unittest.mock import patch

from django.test import override_settings

from commerce_coordinator.apps.commercetools.tests.constants import EXAMPLE_RETURNED_ORDER_STRIPE_SIGNAL_PAYLOAD
from commerce_coordinator.apps.core.tests.utils import CoordinatorSignalReceiverTestCase

# Log using module name.
logger = logging.getLogger(__name__)


@override_settings(
    CC_SIGNALS={
        'commerce_coordinator.apps.core.tests.utils.example_signal': [
            'commerce_coordinator.apps.commercetools.signals.fulfillment_completed_update_ct_line_item',
        ],
    }
)
@patch('commerce_coordinator.apps.commercetools.signals.fulfillment_completed_update_ct_line_item_task')
class FulfillOrderCompletedSendLineItemStateTest(CoordinatorSignalReceiverTestCase):
    """ LMS Fulfillment Order Placed, Line Item State Update Signal Tester"""
    mock_parameters = {
        'entitlement_uuid': '',
        'order_id': 1,
        'line_item_id': 3,
    }

    def test_correct_arguments_passed_fulfillment_true(self, mock_task):
        self.mock_parameters['is_fulfilled'] = True
        _, logs = self.fire_signal()
        self.mock_parameters.pop('is_fulfilled')
        task_mock_parameters = copy(self.mock_parameters)
        logger.info('logs.output: %s', logs.output)
        mock_task.delay.assert_called_once_with(**task_mock_parameters, to_state_key='2u-fulfillment-success-state')

    def test_correct_arguments_passed_fulfillment_false(self, mock_task):
        self.mock_parameters['is_fulfilled'] = False
        _, logs = self.fire_signal()
        self.mock_parameters.pop('is_fulfilled')
        task_mock_parameters = copy(self.mock_parameters)
        logger.info('logs.output: %s', logs.output)
        mock_task.delay.assert_called_once_with(**task_mock_parameters, to_state_key='2u-fulfillment-failure-state')


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
            stripe_refund=self.mock_parameters['stripe_refund'],
            order_number=self.mock_parameters['order_number'],
        )

    def test_correct_response_returned(self, mock_task):
        mock_task.delay.return_value.id = 'bogus_task_id'
        result, _ = self.fire_signal()
        logger.info('result: %s', result)
        self.assertEqual(result[0][1], 'bogus_task_id',
                         'Check reciever result is same as return from task')


@override_settings(
    CC_SIGNALS={
        "commerce_coordinator.apps.core.tests.utils.example_signal": [
            "commerce_coordinator.apps.commercetools.signals.refund_from_paypal",
        ],
    }
)
@patch("commerce_coordinator.apps.commercetools.signals.refund_from_paypal_task")
class RefundFromPaypalTest(CoordinatorSignalReceiverTestCase):
    """PayPal Dashboard Refund Placed, Create Return CT Transaction Signal Tester"""

    mock_parameters = {
        "refund": {
            "id": "paypal_refund_123",
            "amount": "49.99",
            "currency": "USD",
            "status": "COMPLETED",
        },
        "order_number": "2U-123456",
        "paypal_capture_id": "capture_abc123",
    }

    def test_correct_arguments_passed(self, mock_task):
        _, logs = self.fire_signal()
        logger.info("logs.output: %s", logs.output)
        mock_task.delay.assert_called_once_with(
            refund=self.mock_parameters["refund"],
            order_number=self.mock_parameters["order_number"],
            paypal_capture_id=self.mock_parameters["paypal_capture_id"],
        )

    def test_correct_response_returned(self, mock_task):
        mock_task.delay.return_value.id = "paypal_task_id"
        result, _ = self.fire_signal()
        logger.info("result: %s", result)
        self.assertEqual(
            result[0][1],
            "paypal_task_id",
            "Check receiver result is same as return from task",
        )


@override_settings(
    CC_SIGNALS={
        "commerce_coordinator.apps.core.tests.utils.example_signal": [
            "commerce_coordinator.apps.commercetools.signals.refund_from_mobile",
        ],
    }
)
@patch("commerce_coordinator.apps.commercetools.signals.refund_from_mobile_task")
class RefundFromMobileTest(CoordinatorSignalReceiverTestCase):
    """Mobile Platform Refund, Create Return CT Transaction Signal Tester"""

    mock_parameters = {
        "refund": {
            "id": "mobile_refund_123",
            "amount": "99.99",
            "currency": "USD",
            "status": "completed",
        },
        "payment_interface": "ios_iap_edx",
    }

    def test_correct_arguments_passed(self, mock_task):
        _, logs = self.fire_signal()
        logger.info("logs.output: %s", logs.output)
        mock_task.delay.assert_called_once_with(
            refund=self.mock_parameters["refund"],
            payment_interface=self.mock_parameters["payment_interface"],
        )

    def test_correct_response_returned(self, mock_task):
        mock_task.delay.return_value.id = "mobile_task_id"
        result, _ = self.fire_signal()
        logger.info("result: %s", result)
        self.assertEqual(
            result[0][1],
            "mobile_task_id",
            "Check receiver result is same as return from task",
        )
