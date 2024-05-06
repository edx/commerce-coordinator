""" Commercetools Testing Mocks """

from unittest.mock import MagicMock

from commercetools.platform.models import ReturnInfo, ReturnPaymentState, TransactionType

from commerce_coordinator.apps.commercetools.tests.conftest import (
    gen_customer,
    gen_line_item_state,
    gen_order,
    gen_payment,
    gen_return_item
)
from commerce_coordinator.apps.commercetools.tests.constants import EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD


class SendRobustSignalMock(MagicMock):
    """
    A mock send_robust call that always returns
    """

    def mock_receiver(self):
        pass  # pragma: no cover

    return_value = [
        (mock_receiver, 'bogus_task_id'),
    ]


class CTOrderByIdMock(MagicMock):
    """
    A mock get_order_by_id call that always returns
    EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD in the shape of format_signal_results.
    """
    return_value = gen_order(EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD['order_number'])


class CTLineItemStateByKeyMock(MagicMock):
    return_value = gen_line_item_state()


def gen_updated_line_item_state_order():
    """jsdjkasbdj"""
    order = gen_order(EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD['order_number'])
    order.version = 8
    return order


def get_order_with_bad_state_key():
    """Modify a canned order to have a bad transition/workflow state key"""
    order = gen_order(EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD['order_number'])
    order.state.obj.key = "XXXXXXX"
    return order


def get_order_with_missing_state():
    """Modify a canned order to have a bad transition/workflow state key"""
    order = gen_order(EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD['order_number'])
    order.state = None
    return order


def gen_payment_with_charge_transaction():
    """Modify payment to have TransactionType.CHARGE to allow for refund"""
    payment = gen_payment()
    payment.transactions[0].type = TransactionType.CHARGE
    return payment


def gen_order_with_return_item():
    """Modify order to have a return item"""
    returned_order = gen_order(EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD['order_number'])
    return_item = gen_return_item("mock_return_item_id", ReturnPaymentState.REFUNDED)
    return_info = ReturnInfo(items=[return_item])
    returned_order.return_info.append(return_info)
    return returned_order


class CTOrderBadStateKeyByIdMock(MagicMock):
    """
    A mock get_order_by_id call that always returns with a bad state
    """
    return_value = get_order_with_bad_state_key()


class CTOrderMissingStateByIdMock(MagicMock):
    """
    A mock get_order_by_id call that always returns with a missing state
    """
    return_value = get_order_with_missing_state()


class CTCustomerByIdMock(MagicMock):
    """
    A mock get_customer_by_id call that always returns
    EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD in the shape of format_signal_results.
    """
    return_value = gen_customer("hiya@text.example", "jim_34")


class CTUpdateLineItemState(MagicMock):
    return_value = gen_updated_line_item_state_order()


class CTPaymentByKey(MagicMock):
    return_value = gen_payment_with_charge_transaction()


class CTReturnItemCreateMock(MagicMock):
    return_value = gen_order_with_return_item()
