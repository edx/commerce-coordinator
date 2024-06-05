"""
Commercetools app Task Tests
"""

import logging
import stripe
from unittest.mock import patch

from commercetools import CommercetoolsError
from django.test import TestCase

from commerce_coordinator.apps.commercetools.tasks import update_line_item_state_on_fulfillment_completion, refund_from_stripe_task
from commerce_coordinator.apps.commercetools.tests.constants import EXAMPLE_UPDATE_LINE_ITEM_SIGNAL_PAYLOAD, EXAMPLE_RETURNED_ORDER_STRIPE_CLIENT_PAYLOAD,EXAMPLE_RETURNED_ORDER_STRIPE_SIGNAL_PAYLOAD
from commerce_coordinator.apps.commercetools.tests.conftest import gen_payment
from commerce_coordinator.apps.core.models import User

# Log using module name.
logger = logging.getLogger(__name__)

# Define unit under test.
# Note: if the UUT is part of the class as an ivar, it trims off arg0 as 'self' and
#       claims too many args supplied
fulfillment_uut = update_line_item_state_on_fulfillment_completion
returned_uut = refund_from_stripe_task


@patch('commerce_coordinator.apps.commercetools.tasks.CommercetoolsAPIClient')
class UpdateLineItemStateOnFulfillmentCompletionTaskTest(TestCase):
    """ Update Line Item State on Fulfillment Completion Task Test """

    @staticmethod
    def unpack_for_uut(values):
        """ Unpack the dictionary in the order required for the UUT """
        return (
            values['order_id'],
            values['order_version'],
            values['line_item_id'],
            values['item_quantity'],
            values['from_state_id'],
            values['to_state_key']
        )

    def setUp(self):
        User.objects.create(username='test-user', lms_user_id=4)

    def test_correct_arguments_passed(self, mock_client):
        '''
        Check calling uut with mock_parameters yields call to client with
        expected_data.
        '''
        _ = fulfillment_uut(*self.unpack_for_uut(EXAMPLE_UPDATE_LINE_ITEM_SIGNAL_PAYLOAD))
        logger.info('mock_client().mock_calls: %s', mock_client().mock_calls)
        mock_client().update_line_item_transition_state_on_fulfillment.assert_called_once_with(
            *list(EXAMPLE_UPDATE_LINE_ITEM_SIGNAL_PAYLOAD.values())
        )

    @patch('commerce_coordinator.apps.commercetools.tasks.logger')
    def test_exception_handling(self, mock_logger, mock_client):
        '''
        Check if an error in the client results in a logged error
        and None returned.
        '''
        mock_client().update_line_item_transition_state_on_fulfillment.side_effect = CommercetoolsError(
            message="Could not update ReturnPaymentState",
            errors="Some error message",
            response={},
            correlation_id="123456"
        )

        result = fulfillment_uut(*self.unpack_for_uut(EXAMPLE_UPDATE_LINE_ITEM_SIGNAL_PAYLOAD))

        mock_logger.error.assert_called_once_with(
            f"Unable to update line item [ {EXAMPLE_UPDATE_LINE_ITEM_SIGNAL_PAYLOAD['line_item_id']} ] "
            "state on fulfillment result with error Some error message and correlation id 123456"
        )

        assert result is None


@patch('commerce_coordinator.apps.commercetools.tasks.CommercetoolsAPIClient')
class ReturnedOrderfromStripeTaskTest(TestCase):
    """ Returned Order From Stripe Task Test """

    @staticmethod
    def unpack_for_uut(values):
        """ Unpack the dictionary in the order required for the UUT """
        return (
            values['payment_intent_id'],
            values['stripe_refund'],
        )

    def setUp(self):
        User.objects.create(username='test-user', lms_user_id=4)

    def test_correct_arguments_passed(self, mock_client):
        '''
        Check calling uut with mock_parameters yields call to client with
        expected_data.
        '''
        mock_payment = gen_payment()
        mock_payment.id = 'f988e0c5-ea44-4111-a7f2-39ecf6af9840'
        mock_client.return_value.get_payment_by_key.return_value = mock_payment

        mock_stripe_refund = stripe.Refund()
        stripe_refund_json = EXAMPLE_RETURNED_ORDER_STRIPE_SIGNAL_PAYLOAD['stripe_refund']
        mock_stripe_refund.update(stripe_refund_json)

        _ = returned_uut(*self.unpack_for_uut(EXAMPLE_RETURNED_ORDER_STRIPE_SIGNAL_PAYLOAD))
        logger.info('mock_client().mock_calls: %s', mock_client().mock_calls)

        mock_client().create_return_payment_transaction.assert_called_once_with(
            payment_id=mock_payment.id,
            payment_version=mock_payment.version,
            stripe_refund=mock_stripe_refund
        )

    @patch('commerce_coordinator.apps.commercetools.tasks.logger')
    def test_exception_handling(self, mock_logger, mock_client):
        '''
        Check if an error in the client results in a logged error
        and None returned.
        '''
        mock_payment = gen_payment()
        mock_payment.id = 'f988e0c5-ea44-4111-a7f2-39ecf6af9840'
        mock_client.return_value.get_payment_by_key.return_value = mock_payment
        mock_client().create_return_payment_transaction.side_effect = CommercetoolsError(
            message="Could not create return transaction",
            errors="Some error message",
            response={},
            correlation_id="123456"
        )

        returned_uut(*self.unpack_for_uut(EXAMPLE_RETURNED_ORDER_STRIPE_SIGNAL_PAYLOAD))

        mock_logger.error.assert_called_once_with(
            f"Unable to create refund transaction for payment [ {EXAMPLE_RETURNED_ORDER_STRIPE_CLIENT_PAYLOAD['payment_id']} ] "
            f"on Stripe refund {EXAMPLE_RETURNED_ORDER_STRIPE_CLIENT_PAYLOAD['stripe_refund']['id']} "
            f"with error Some error message and correlation id 123456"
        )

