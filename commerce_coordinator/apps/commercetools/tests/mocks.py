""" Commercetools Testing Mocks """

from unittest.mock import MagicMock

from commerce_coordinator.apps.commercetools.tests.conftest import gen_customer, gen_order
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
