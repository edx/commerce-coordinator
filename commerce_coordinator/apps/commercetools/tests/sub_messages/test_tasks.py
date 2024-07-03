"""Commercetools Task Tests"""
import logging
from unittest import TestCase
from unittest.mock import MagicMock, call, patch

from commercetools.platform.models import Order as CTOrder
from commercetools.platform.models import ReturnInfo as CTReturnInfo
from commercetools.platform.models import ReturnPaymentState as CTReturnPaymentState
from edx_django_utils.cache import TieredCache

from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient
from commerce_coordinator.apps.commercetools.constants import SOURCE_SYSTEM
from commerce_coordinator.apps.commercetools.sub_messages.tasks import (
    fulfill_order_placed_message_signal_task,
    fulfill_order_returned_signal_task,
    fulfill_order_sanctioned_message_signal_task
)
from commerce_coordinator.apps.commercetools.tests.conftest import MonkeyPatch, gen_return_item
from commerce_coordinator.apps.commercetools.tests.mocks import (
    CTCustomerByIdMock,
    CTLineItemStateByKeyMock,
    CTOrderByIdMock,
    CTPaymentByKey,
    CTReturnItemCreateMock,
    CTUpdateLineItemState,
    SendRobustSignalMock
)
from commerce_coordinator.apps.core.memcache import safe_key
from commerce_coordinator.apps.core.tests.utils import uuid4_str

# Log using module name.
logger = logging.getLogger(__name__)

# Define unit under test.
# Note: if the UUT is part of the class as an ivar, it trims off arg0 as 'self' and
#       claims too many args supplied
fulfill_order_placed_uut = fulfill_order_placed_message_signal_task
fulfill_order_sanctioned_uut = fulfill_order_sanctioned_message_signal_task
fulfill_order_returned_uut = fulfill_order_returned_signal_task


def gen_example_fulfill_payload():
    return {
        'order_id': uuid4_str(),
        'order_number': '2U-000000',
        'line_item_state_id': uuid4_str(),
        'order_line_id': uuid4_str(),
        'source_system': SOURCE_SYSTEM,
        'message_id': uuid4_str()
    }


class CommercetoolsAPIClientMock(MagicMock):
    """Mock for CommercetoolsAPIClient with Order and Customer mocks/IDs"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # This is a slightly hacked mock. Thus all of these values need to be invoked via return_value.

        self.example_payload = gen_example_fulfill_payload()
        self.order_id = self.example_payload['order_id']
        self.order_number = self.example_payload['order_number']
        self.line_item_state_id = self.example_payload['line_item_state_id']
        self.customer_id = uuid4_str()
        self.processing_line_item_id = uuid4_str()
        self.cache_key = safe_key(key=self.order_id, key_prefix='send_order_confirmation_email', version='1')

        self.order_mock = CTOrderByIdMock()
        self.customer_mock = CTCustomerByIdMock()
        self.payment_mock = CTPaymentByKey()

        self.state_by_key_mock = CTLineItemStateByKeyMock()
        self.updated_line_item_mock = CTUpdateLineItemState()
        self.create_return_item_mock = CTReturnItemCreateMock()

        self.order_mock.return_value.id = self.order_id
        self.order_mock.return_value.order_number = self.order_number
        self.customer_mock.return_value.id = self.customer_id
        self.order_mock.return_value.customer_id = self.customer_id
        self.state_by_key_mock.return_value.id = self.processing_line_item_id

        self.get_order_by_id = self.order_mock
        self.get_customer_by_id = self.customer_mock
        self.get_state_by_key = self.state_by_key_mock
        self.get_payment_by_key = self.payment_mock
        self.update_line_item_transition_state_on_fulfillment = self.updated_line_item_mock
        self.create_return_for_order = self.create_return_item_mock
        self.create_return_payment_transaction = self.payment_mock
        self.update_return_payment_state_after_successful_refund = self.order_mock

        self.expected_order = self.order_mock.return_value
        self.expected_customer = self.customer_mock.return_value


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
            values['line_item_state_id'],
            values['source_system'],
            values['message_id']
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

    @patch('commerce_coordinator.apps.commercetools.sub_messages.tasks.is_edx_lms_order',
           return_value=False)
    def test_not_lms_order(self, _fn, _ct_client_init: CommercetoolsAPIClientMock, _lms_signal):
        """
        Check calling uut with mock_parameters yields call to client with
        expected_data.
        """
        mock_values = _ct_client_init.return_value

        ret_val = self.get_uut()(*self.unpack_for_uut(mock_values.example_payload))

        self.assertTrue(ret_val)
        mock_values.order_mock.assert_called_once_with(mock_values.order_id)
        mock_values.customer_mock.assert_called_once_with(mock_values.customer_id)
        self.assertFalse(TieredCache.get_cached_response(mock_values.cache_key).is_found)


@patch('commerce_coordinator.apps.commercetools.sub_messages.tasks.LMSAPIClient.deactivate_user',
       return_value=None)
@patch('commerce_coordinator.apps.commercetools.sub_messages.tasks.CommercetoolsAPIClient',
       new_callable=CommercetoolsAPIClientMock)
class OrderSanctionedMessageSignalTaskTests(TestCase):
    """Tests for the fulfill_order_sanctioned_message_signal_task"""

    @staticmethod
    def unpack_for_uut(values):
        """ Unpack the dictionary in the order required for the UUT """
        return (
            values['order_id'],
        )

    @staticmethod
    def get_uut():
        return fulfill_order_sanctioned_uut

    def test_correct_arguments_passed(self, _ct_client_init: CommercetoolsAPIClientMock, _fn_mock):
        """
        Check calling uut with mock_parameters yields call to client with
        expected_data.
        """
        mock_values = _ct_client_init.return_value
        _ = self.get_uut()(*self.unpack_for_uut(mock_values.example_payload))

        mock_values.order_mock.assert_called_once_with(mock_values.expected_order.id)
        mock_values.customer_mock.assert_called_once_with(mock_values.expected_customer.id)

    @patch('commerce_coordinator.apps.commercetools.sub_messages.tasks.is_edx_lms_order',
           return_value=None)
    def test_not_lms_order(self, _fn, _ct_client_init: CommercetoolsAPIClientMock, _fn_mock):
        """
        Check calling uut with mock_parameters yields call to client with
        expected_data.
        """
        mock_values = _ct_client_init.return_value

        ret_val = self.get_uut()(*self.unpack_for_uut(mock_values.example_payload))

        self.assertTrue(ret_val)
        mock_values.order_mock.assert_called_once_with(mock_values.order_id)
        mock_values.customer_mock.assert_called_once_with(mock_values.customer_id)

    @patch('commerce_coordinator.apps.commercetools.sub_messages.tasks.get_edx_order_workflow_state_key',
           return_value=None)
    def test_missing_order_workflow_state(self, _fn, _ct_client_init: CommercetoolsAPIClientMock, _fn_mock):
        """
        Check calling uut with mock_parameters yields call to client with
        expected_data.
        """
        mock_values = _ct_client_init.return_value

        ret_val = self.get_uut()(*self.unpack_for_uut(mock_values.example_payload))

        self.assertTrue(ret_val)
        mock_values.order_mock.assert_called_once_with(mock_values.order_id)
        mock_values.customer_mock.assert_called_once_with(mock_values.customer_id)

    @patch('commerce_coordinator.apps.commercetools.sub_messages.tasks.get_edx_is_sanctioned',
           return_value=False)
    def test_order_not_sanctioned(self, _fn, _ct_client_init: CommercetoolsAPIClientMock, _fn_mock):
        """
        Check calling uut with mock_parameters yields call to client with
        expected_data.
        """
        mock_values = _ct_client_init.return_value

        ret_val = self.get_uut()(*self.unpack_for_uut(mock_values.example_payload))
        self.assertFalse(ret_val)
        mock_values.order_mock.assert_called_once_with(mock_values.order_id)
        mock_values.customer_mock.assert_called_once_with(mock_values.customer_id)

    @patch('commerce_coordinator.apps.commercetools.sub_messages.tasks.get_edx_is_sanctioned',
           return_value=True)
    def test_order_sanctioned(self, _fn, _ct_client_init: CommercetoolsAPIClientMock, _fn_mock):
        """
        Check calling uut with mock_parameters yields call to client with
        expected_data.
        """
        mock_values = _ct_client_init.return_value

        ret_val = self.get_uut()(*self.unpack_for_uut(mock_values.example_payload))
        self.assertTrue(ret_val)
        mock_values.order_mock.assert_called_once_with(mock_values.order_id)
        mock_values.customer_mock.assert_called_once_with(mock_values.customer_id)


class OrderReturnedMessageSignalTaskTests(TestCase):
    """Tests for the fulfill_order_returned_signal_task"""

    def setUp(self):
        super().setUp()
        self.mock = CommercetoolsAPIClientMock()

        MonkeyPatch.monkey(
            CommercetoolsAPIClient,
            {
                '__init__': lambda _: None,
                'get_order_by_id': self.mock.get_order_by_id,
                'get_customer_by_id': self.mock.get_customer_by_id,
                'get_payment_by_key': self.mock.get_payment_by_key,
                'create_return_for_order': self.mock.create_return_for_order,
                'create_return_payment_transaction': self.mock.create_return_payment_transaction,
                'update_return_payment_state_after_successful_refund':
                    self.mock.update_return_payment_state_after_successful_refund
            }
        )

    def tearDown(self):
        MonkeyPatch.unmonkey(CommercetoolsAPIClient)
        super().tearDown()

    @staticmethod
    def unpack_for_uut(values):
        """ Unpack the dictionary in the order required for the UUT """
        return (
            values['order_id'],
            values['order_line_id'],
        )

    @staticmethod
    def get_uut():
        return fulfill_order_returned_uut

    # todo this flow is broken
    @patch('commerce_coordinator.apps.commercetools.sub_messages.tasks.is_edx_lms_order')
    @patch('commerce_coordinator.apps.stripe.pipeline.StripeAPIClient')
    def test_correct_arguments_passed_already_refunded_doest_break(self, _stripe_api_mock, _lms_signal):
        """
        Check calling uut with mock_parameters yields call to client with
        expected_data.
        """
        mock_values = self.mock

        ret_val = self.get_uut()(*self.unpack_for_uut(self.mock.example_payload))

        self.assertTrue(ret_val)
        mock_values.order_mock.assert_has_calls([call(mock_values.order_id), call(order_id=mock_values.order_id)])
        mock_values.customer_mock.assert_called_once_with(mock_values.customer_id)

    @patch('commerce_coordinator.apps.commercetools.sub_messages.tasks.is_edx_lms_order')
    @patch('commerce_coordinator.apps.stripe.pipeline.StripeAPIClient')
    @patch('commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.create_return_for_order')
    def test_correct_arguments_passed_valid_stripe_refund(
        self,
        _return_order_mock: MagicMock,
        _stripe_api_mock: MagicMock,
        _lms_signal
    ):
        """
        Check calling uut with mock_parameters yields call to client with
        expected_data.
        """
        mock_values = self.mock
        mock_values.order_mock.return_value.return_info = []
        _stripe_api_mock.return_value.refund_payment_intent.return_value.return_value = {
            "id": "123",
            "status": "succeeded"
        }
        _return_order_mock.return_value = CTOrder.deserialize(mock_values.order_mock.return_value.serialize())
        _return_order_mock.return_value.return_info.append(
            CTReturnInfo(items=[gen_return_item("mock_return_item_id", CTReturnPaymentState.INITIAL)])
        )

        ret_val = self.get_uut()(*self.unpack_for_uut(self.mock.example_payload))

        self.assertTrue(ret_val)
        mock_values.order_mock.assert_has_calls([call(mock_values.order_id), call(order_id=mock_values.order_id)])
        mock_values.customer_mock.assert_called_once_with(mock_values.customer_id)
        _stripe_api_mock.return_value.refund_payment_intent.assert_called_once()
