"""Commercetools Task Tests"""

import logging
from unittest import TestCase
from unittest.mock import MagicMock, patch

from edx_django_utils.cache import TieredCache

from commerce_coordinator.apps.commercetools.constants import SOURCE_SYSTEM
from commerce_coordinator.apps.commercetools.sub_messages.tasks import fulfill_order_placed_message_signal_task
from commerce_coordinator.apps.commercetools.tests.mocks import (
    CTCustomerByIdMock,
    CTOrderByIdMock,
    SendRobustSignalMock
)
from commerce_coordinator.apps.core.memcache import safe_key
from commerce_coordinator.apps.core.tests.utils import uuid4_str


def gen_example_fulfill_payload():
    return {
        'order_id': uuid4_str(),
        'source_system': SOURCE_SYSTEM,
    }


class CommercetoolsAPIClientMock(MagicMock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # This is a slightly hacked mock. Thus all of these values need to be invoked via return_value.

        self.example_payload = gen_example_fulfill_payload()
        self.order_id = self.example_payload['order_id']
        self.cache_key = safe_key(key=self.order_id, key_prefix='send_order_confirmation_email', version='1')

        self.order_mock = CTOrderByIdMock()
        self.customer_mock = CTCustomerByIdMock()

        self.order_mock.return_value.id = self.order_id
        self.order_mock.return_value.customer_id = self.customer_mock.return_value.id

        self.get_order_by_id = self.order_mock
        self.get_customer_by_id = self.customer_mock

        self.expected_order = self.order_mock.return_value
        self.expected_customer = self.customer_mock.return_value




# Log using module name.
logger = logging.getLogger(__name__)

# Define unit under test.
# Note: if the UUT is part of the class as an ivar, it trims off arg0 as 'self' and
#       claims too many args supplied
fulfill_order_placed_uut = fulfill_order_placed_message_signal_task


@patch('commerce_coordinator.apps.commercetools.sub_messages.tasks.fulfill_order_placed_signal.send_robust',
       new_callable=SendRobustSignalMock)
@patch('commerce_coordinator.apps.commercetools.sub_messages.tasks.CommercetoolsAPIClient',
       new_callable=CommercetoolsAPIClientMock)
class FulfillOrderPlacedMessageSignalTaskTests(TestCase):
    """Tests for the fulfill_order_placed_message_signal_task"""

    @staticmethod
    def unpack_for_uut(values):
        """ Unpack the dictionary in the order required for the UUT """
        return (
            values['order_id'],
            values['source_system']
        )

    @staticmethod
    def get_uut():
        return fulfill_order_placed_uut

    def test_correct_arguments_passed(self, _ct_client_init: CommercetoolsAPIClientMock, _lms_signal):
        """
        Check calling uut with mock_parameters yields call to client with
        expected_data.
        """
        mock_values = _ct_client_init.return_value
        _ = self.get_uut()(*self.unpack_for_uut(mock_values.example_payload))

        mock_values.order_mock.assert_called_once_with(mock_values.expected_order.id)
        mock_values.customer_mock.assert_called_once_with(mock_values.expected_customer.id)
        self.assertTrue(TieredCache.get_cached_response(mock_values.cache_key).is_found)
