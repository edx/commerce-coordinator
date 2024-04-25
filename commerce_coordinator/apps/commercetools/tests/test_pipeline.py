"""Commercetools pipeline test cases"""

from unittest import TestCase
from unittest.mock import patch

from commercetools.platform.models import ReturnInfo, ReturnPaymentState, ReturnShipmentState, TransactionType
from rest_framework.test import APITestCase

from commerce_coordinator.apps.commercetools.constants import COMMERCETOOLS_ORDER_MANAGEMENT_SYSTEM
from commerce_coordinator.apps.commercetools.pipeline import (
    CreateReturnForCommercetoolsOrder,
    CreateReturnPaymentTransaction,
    GetCommercetoolsOrders,
    UpdateCommercetoolsOrderReturnPaymentStatus
)
from commerce_coordinator.apps.commercetools.tests._test_cases import MonkeyPatchedGetOrderTestCase
from commerce_coordinator.apps.commercetools.tests.conftest import (
    APITestingSet,
    gen_order,
    gen_payment,
    gen_return_item
)
from commerce_coordinator.apps.core.constants import ORDER_HISTORY_PER_SYSTEM_REQ_LIMIT
from commerce_coordinator.apps.core.exceptions import InvalidFilterType


class PipelineTests(MonkeyPatchedGetOrderTestCase):
    """Commercetools pipeline testcase"""

    def test_pipeline(self):
        """Ensure pipeline is functioning as expected"""

        pipe = GetCommercetoolsOrders("test_pipe", None)
        ret = pipe.run_filter(
            {
                "edx_lms_user_id": 127,
                "page_size": ORDER_HISTORY_PER_SYSTEM_REQ_LIMIT,
                "page": 0,
            },
            []
        )

        self.assertEqual(len(ret['order_data']), len(self.orders))


class CommercetoolsOrLegacyEcommerceRefundPipelineTests(APITestCase):
    """
    Rollout pipeline tests to determine which system applies the refund
    for given order.

    """

    def setUp(self):
        super().setUp()
        self.client_set = APITestingSet.new_instance()
        mock_response_order = gen_order("mock_id")
        mock_response_order.version = "1"
        self.mock_response_order = mock_response_order
        mock_response_return_item = gen_return_item("mock_return_item_id", ReturnPaymentState.INITIAL)
        mock_response_return_info = ReturnInfo(items=[mock_response_return_item])
        mock_response_order.return_info.append(mock_response_return_info)
        self.returned_order = mock_response_order
        self.returned_payment = gen_payment()
        mock_response_payment = gen_payment()
        mock_response_payment.transactions[0].type = TransactionType.CHARGE
        self.mock_response_payment = mock_response_payment

    def tearDown(self):
        del self.client_set
        super().tearDown()

    def test_legacy_ecommerce_refund(self):
        refund_pipe = CreateReturnForCommercetoolsOrder("test_pipe", None)
        ret = refund_pipe.run_filter(
            active_order_management_system="Legacy",
            order_id="mock_id",
            order_line_id="mock_line_id",
            order_data=self.mock_response_order
        )
        self.assertEqual(ret, {})

    @patch('commerce_coordinator.apps.rollout.utils.is_commercetools_line_item_already_refunded')
    @patch('commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_order_by_id')
    @patch('commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.create_return_for_order')
    def test_commercetools_order_refund(self, mock_returned_order, mock_order, mock_ct_refund):
        mock_ct_refund.return_value = False
        mock_order.return_value = self.mock_response_order
        mock_returned_order.return_value = self.returned_order

        refund_pipe = CreateReturnForCommercetoolsOrder("test_pipe", None)
        ret = refund_pipe.run_filter(
            active_order_management_system=COMMERCETOOLS_ORDER_MANAGEMENT_SYSTEM,
            order_id="mock_id",
            order_line_id="mock_line_id",
            order_data=self.mock_response_order
        )
        mock_order_result = ret['returned_order']

        self.assertEqual(mock_order_result, self.returned_order)
        self.assertEqual(mock_order_result.return_info[1].items[0].shipment_state, ReturnShipmentState.RETURNED)

    @patch('commerce_coordinator.apps.rollout.utils.is_commercetools_line_item_already_refunded')
    @patch('commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_order_by_id')
    def test_commercetools_order_item_already_refunded(self, mock_order, mock_ct_refund):
        mock_order.return_value = self.mock_response_order
        mock_ct_refund.return_value = True

        refund_pipe = CreateReturnForCommercetoolsOrder("test_pipe", None)
        with self.assertRaises(InvalidFilterType) as exc:
            refund_pipe.run_filter(
                active_order_management_system=COMMERCETOOLS_ORDER_MANAGEMENT_SYSTEM,
                order_id="mock_id",
                order_line_id="order_line_id",
                order_data=self.mock_response_order
            )

        self.assertEqual(
            str(exc.exception),
            'Refund already created for order mock_id with order line id order_line_id'
        )

    @patch('commerce_coordinator.apps.commercetools.utils.has_refund_transaction')
    @patch('commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_payment_by_key')
    @patch('commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.create_return_payment_transaction')
    def test_commercetools_transaction_create(self, mock_returned_payment, mock_payment, mock_has_refund):
        mock_has_refund.return_value = False
        mock_payment.return_value = self.mock_response_payment
        mock_returned_payment.return_value = self.returned_payment

        refund_pipe = CreateReturnPaymentTransaction("test_pipe", None)
        ret = refund_pipe.run_filter(
            payment_data=self.mock_response_payment,
            refund_response={"payment_intent": "mock_payment_intent"},
            active_order_management_system=COMMERCETOOLS_ORDER_MANAGEMENT_SYSTEM,
            has_been_refunded=False
        )
        mock_payment_result = ret['returned_payment']

        self.assertEqual(mock_payment_result, self.returned_payment)
        self.assertEqual(mock_payment_result.transactions[0].type, TransactionType.REFUND)

    @patch('commerce_coordinator.apps.commercetools.utils.has_refund_transaction')
    @patch('commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_payment_by_key')
    @patch('commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.create_return_payment_transaction')
    def test_commercetools_transaction_create_no_payment_data(self, mock_returned_payment,
                                                              mock_payment, mock_has_refund):
        mock_has_refund.return_value = False
        mock_payment.return_value = self.mock_response_payment
        mock_returned_payment.return_value = self.returned_payment

        refund_pipe = CreateReturnPaymentTransaction("test_pipe", None)
        ret = refund_pipe.run_filter(
            payment_data=None,
            refund_response={"payment_intent": "mock_payment_intent"},
            active_order_management_system=COMMERCETOOLS_ORDER_MANAGEMENT_SYSTEM,
            has_been_refunded=False
        )
        mock_payment_result = ret['returned_payment']

        self.assertEqual(mock_payment_result, self.returned_payment)
        self.assertEqual(mock_payment_result.transactions[0].type, TransactionType.REFUND)


class OrderReturnPipelineTests(TestCase):
    """Commercetools pipeline testcase for order updates on returns"""
    def setUp(self) -> None:
        order_data = gen_order("mock_order_id")
        return_item = gen_return_item("mock_return_item_id", ReturnPaymentState.INITIAL)
        return_info = ReturnInfo(items=[return_item])
        order_data.return_info.append(return_info)
        self.update_order_data = order_data

        order_respose_data = gen_order("mock_order_id")
        order_respose_data.version = "8"
        return_item_response = gen_return_item("mock_return_item_id", ReturnPaymentState.REFUNDED)
        return_info_response = ReturnInfo(items=[return_item_response])
        order_respose_data.return_info.append(return_info_response)
        self.update_order_response = order_respose_data

    @patch(
        'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient'
        '.update_return_payment_state_after_successful_refund'
    )
    def test_pipeline(self, mock_order_return_update):
        """Ensure pipeline is functioning as expected"""

        pipe = UpdateCommercetoolsOrderReturnPaymentStatus("test_pipe", None)
        mock_order_return_update.return_value = self.update_order_response
        ret = pipe.run_filter(returned_order=self.update_order_data, return_line_item_return_id="mock_return_item_id")
        result_data = ret['returned_order']
        self.assertEqual(result_data, self.update_order_response)
        self.assertEqual(result_data.return_info[1].items[0].payment_state, ReturnPaymentState.REFUNDED)
