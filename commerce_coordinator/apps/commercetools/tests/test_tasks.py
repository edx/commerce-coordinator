"""
Commercetools app Task Tests
"""

import logging
from unittest.mock import patch

from commercetools import CommercetoolsError
from django.test import TestCase

from commerce_coordinator.apps.commercetools.tasks import update_line_item_state_on_fulfillment_completion
from commerce_coordinator.apps.commercetools.tests.constants import EXAMPLE_UPDATE_LINE_ITEM_SIGNAL_PAYLOAD
from commerce_coordinator.apps.core.models import User

# Log using module name.
logger = logging.getLogger(__name__)

# Define unit under test.
# Note: if the UUT is part of the class as an ivar, it trims off arg0 as 'self' and
#       claims too many args supplied
uut = update_line_item_state_on_fulfillment_completion


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
        _ = uut(*self.unpack_for_uut(EXAMPLE_UPDATE_LINE_ITEM_SIGNAL_PAYLOAD))
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

        result = uut(*self.unpack_for_uut(EXAMPLE_UPDATE_LINE_ITEM_SIGNAL_PAYLOAD))

        mock_logger.error.assert_called_once_with(
            f"Unable to update line item [ {EXAMPLE_UPDATE_LINE_ITEM_SIGNAL_PAYLOAD['line_item_id']} ] "
            "state on fulfillment result with error Some error message and correlation id 123456"
        )

        assert result is None
