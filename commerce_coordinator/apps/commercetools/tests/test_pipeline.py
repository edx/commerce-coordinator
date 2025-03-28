"""Commercetools pipeline test cases"""

from unittest import TestCase
from unittest.mock import patch

from commercetools.platform.models import ReturnInfo, ReturnPaymentState, ReturnShipmentState, TransactionType
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from rest_framework.test import APITestCase

from commerce_coordinator.apps.commercetools.catalog_info.constants import (
    EDX_PAYPAL_PAYMENT_INTERFACE_NAME,
    EDX_STRIPE_PAYMENT_INTERFACE_NAME
)
from commerce_coordinator.apps.commercetools.constants import COMMERCETOOLS_ORDER_MANAGEMENT_SYSTEM
from commerce_coordinator.apps.commercetools.pipeline import (
    AnonymizeRetiredUser,
    CreateReturnForCommercetoolsOrder,
    CreateReturnPaymentTransaction,
    GetCommercetoolsOrders,
    UpdateCommercetoolsOrderReturnPaymentStatus
)
from commerce_coordinator.apps.commercetools.tests._test_cases import MonkeyPatchedGetOrderTestCase
from commerce_coordinator.apps.commercetools.tests.conftest import (
    APITestingSet,
    gen_customer,
    gen_order,
    gen_payment,
    gen_retired_customer,
    gen_return_item
)
from commerce_coordinator.apps.core.constants import ORDER_HISTORY_PER_SYSTEM_REQ_LIMIT, PipelineCommand
from commerce_coordinator.apps.core.exceptions import InvalidFilterType
from commerce_coordinator.apps.paypal.pipeline import RefundPayPalPayment

User = get_user_model()


class PipelineTests(MonkeyPatchedGetOrderTestCase):
    """Commercetools pipeline testcase"""

    @patch('commerce_coordinator.apps.commercetools.pipeline.is_redirect_to_commercetools_enabled_for_user')
    def test_pipeline(self, is_redirect_mock):
        """Ensure pipeline is functioning as expected"""

        is_redirect_mock.return_value = True
        request = RequestFactory()
        request.user = User.objects.create_user(
            username='test', email='test@example.com', password='secret'
        )
        pipe = GetCommercetoolsOrders("test_pipe", None)
        ret = pipe.run_filter(
            request,
            {
                "edx_lms_user_id": 127,
                "customer_id": None,
                "email": "test@example.com",
                "username": "test",
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
            order_line_item_id="mock_line_id"
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
            order_line_item_id="mock_line_id"
        )
        mock_order_result = ret['returned_order']

        self.assertEqual(mock_order_result, self.returned_order)
        self.assertEqual(mock_order_result.return_info[1].items[0].shipment_state, ReturnShipmentState.RETURNED)

    @patch('commerce_coordinator.apps.rollout.utils.is_commercetools_line_item_already_refunded')
    @patch('commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_order_by_id')
    def test_commercetools_order_item_already_refunded(self, mock_order, mock_ct_refund):
        mock_response_order = gen_order("mock_id")
        mock_response_return_item = gen_return_item("order_line_id", ReturnPaymentState.REFUNDED)
        mock_response_return_info = ReturnInfo(items=[mock_response_return_item])
        mock_response_order.return_info.append(mock_response_return_info)

        mock_order.return_value = mock_response_order
        mock_ct_refund.return_value = True

        refund_pipe = CreateReturnForCommercetoolsOrder("test_pipe", None)
        with self.assertRaises(InvalidFilterType) as exc:
            refund_pipe.run_filter(
                active_order_management_system=COMMERCETOOLS_ORDER_MANAGEMENT_SYSTEM,
                order_id="mock_id",
                order_line_item_id="order_line_id"
            )

        self.assertEqual(
            str(exc.exception),
            'Refund already created for order mock_id with order line item id order_line_id'
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
            has_been_refunded=False,
            payment_intent_id="pi_4MtwBwLkdIwGlenn28a3tqPa",
            psp=EDX_STRIPE_PAYMENT_INTERFACE_NAME
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
            has_been_refunded=False,
            payment_intent_id="pi_4MtwBwLkdIwGlenn28a3tqPa",
            psp=EDX_STRIPE_PAYMENT_INTERFACE_NAME
        )
        mock_payment_result = ret['returned_payment']

        self.assertEqual(mock_payment_result, self.returned_payment)
        self.assertEqual(mock_payment_result.transactions[0].type, TransactionType.REFUND)

    @patch('commerce_coordinator.apps.commercetools.utils.has_refund_transaction')
    @patch('commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_payment_by_key')
    @patch('commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.create_return_payment_transaction')
    @patch('commerce_coordinator.apps.commercetools.pipeline.log.info')
    def test_commercetools_create_transaction_with_free_order(self, mock_logger, mock_returned_payment,
                                                              mock_payment, mock_has_refund):
        mock_has_refund.return_value = False
        mock_payment.return_value = None
        mock_returned_payment.return_value = None

        refund_pipe = CreateReturnPaymentTransaction("test_pipe", None)
        refund_pipe.run_filter(
            payment_data=None,
            refund_response={},
            active_order_management_system=COMMERCETOOLS_ORDER_MANAGEMENT_SYSTEM,
            has_been_refunded=False,
            payment_intent_id=None,
            psp=None
        )

        mock_logger.assert_called_once_with('[CreateReturnPaymentTransaction] Payment data not found,'
                                            ' skipping refund payment transaction creation')

    @patch('commerce_coordinator.apps.commercetools.pipeline.log.info')
    def test_commercetools_transaction_create_has_refund(self, mock_logger):
        refund_pipe = CreateReturnPaymentTransaction("test_pipe", None)
        refund_pipe.run_filter(
            payment_data=self.mock_response_payment,
            refund_response="charge_already_refunded",
            active_order_management_system=COMMERCETOOLS_ORDER_MANAGEMENT_SYSTEM,
            has_been_refunded=True,
            payment_intent_id="pi_4MtwBwLkdIwGlenn28a3tqPa",
            psp=EDX_STRIPE_PAYMENT_INTERFACE_NAME
        )
        mock_logger.assert_called_once_with('[CreateReturnPaymentTransaction] refund has already been processed, '
                                            'skipping refund payment transaction creation')

    @patch('commerce_coordinator.apps.commercetools.pipeline.log.info')
    def test_commercetools_transaction_create_psp_error(self, mock_logger):
        refund_pipe = CreateReturnPaymentTransaction("test_pipe", None)
        refund_pipe.run_filter(
            payment_data=self.mock_response_payment,
            refund_response={"payment_intent": "mock_payment_intent"},
            active_order_management_system=COMMERCETOOLS_ORDER_MANAGEMENT_SYSTEM,
            has_been_refunded=False,
            payment_intent_id="pi_4MtwBwLkdIwGlenn28a3tqPa",
            psp=EDX_STRIPE_PAYMENT_INTERFACE_NAME,
            psp_refund_error='refund amount greater than unrefunded amount on charged amount'
        )
        mock_logger.assert_called_once_with('[CreateReturnPaymentTransaction] PSP Refund error, '
                                            'skipping refund payment transaction creation')


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
        ret = pipe.run_filter(
            order_data=self.update_order_data, returned_order=self.update_order_data,
            payment_intent_id="mock_payment_intent_id", amount_in_cents=10000,
            return_line_items={"mock_line_item_id": 'mock_return_item_id'},
            refunded_line_item_refunds=["refunded_line_item_refunds"],
            return_line_entitlement_ids={'mock_return_item_id': 'mock_entitlement_id'}
        )
        result_data = ret['returned_order']
        self.assertEqual(result_data, self.update_order_response)
        self.assertEqual(result_data.return_info[1].items[0].payment_state, ReturnPaymentState.REFUNDED)

    @patch('commerce_coordinator.apps.commercetools.pipeline.log.info')
    def test_pipeline_with_psp_error(self, mock_logger):
        """Ensure pipeline is functioning as expected"""

        pipe = UpdateCommercetoolsOrderReturnPaymentStatus("test_pipe", None)

        pipe.run_filter(
            psp_refund_error='refund amount greater than unrefunded amount on charged amount'
        )
        mock_logger.assert_called_once_with('[UpdateCommercetoolsOrderReturnPaymentStatus] PSP Refund error, '
                                            'skipping order refund payment transaction updation')

    @patch('commerce_coordinator.apps.commercetools.pipeline.log.info')
    def test_pipeline_with_free_order(self, mock_logger):
        """Ensure pipeline is functioning as expected"""

        pipe = UpdateCommercetoolsOrderReturnPaymentStatus("test_pipe", None)

        pipe.run_filter(
            psp=None,
            payment_intent_id=None,
        )
        mock_logger.assert_called_once_with('[UpdateCommercetoolsOrderReturnPaymentStatus] Payment data not found,'
                                            ' skipping order refund payment transaction updation')


class AnonymizeRetiredUserPipelineTests(TestCase):
    """Commercetools pipeline testcase for CT customer retirement after account deletion in LMS"""

    def setUp(self) -> None:
        self.customer_data = gen_customer("mock_email", "mock_username")

        mock_anonymized_first_name = "retired_user_b90b0331d08e19eaef586"
        mock_anonymized_last_name = "retired_user_b45093f6f96eac6421f8"
        mock_anonymized_email = "retired_user_149c01e31901998b11"
        mock_anonymized_lms_username = "retired_user_8d2382cd8435a1c520"
        self.mock_anonymize_result = {
            "first_name": mock_anonymized_first_name,
            "last_name": mock_anonymized_last_name,
            "email": mock_anonymized_email,
            "lms_username": mock_anonymized_lms_username
        }
        self.update_customer_response = gen_retired_customer(
            mock_anonymized_first_name,
            mock_anonymized_last_name,
            mock_anonymized_email,
            mock_anonymized_lms_username
        )
        self.mock_lms_user_id = 127

    @patch(
        'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient'
        '.retire_customer_anonymize_fields'
    )
    @patch(
        'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient'
        '.get_customer_by_lms_user_id'
    )
    @patch('commerce_coordinator.apps.commercetools.pipeline.create_retired_fields')
    def test_pipeline(self, mock_anonymize_fields, mock_customer_by_lms_id, mock_anonymized_customer_return):
        """Ensure pipeline is functioning as expected"""

        pipe = AnonymizeRetiredUser("test_pipe", None)
        mock_customer_by_lms_id.return_value = self.customer_data
        mock_anonymize_fields.return_value = self.mock_anonymize_result
        mock_anonymized_customer_return.return_value = self.update_customer_response
        ret = pipe.run_filter(lms_user_id=self.mock_lms_user_id)
        result_data = ret['returned_customer']
        self.assertEqual(result_data, self.update_customer_response)


class RefundPayPalPaymentTests(TestCase):
    """Tests for RefundPayPalPayment pipeline step"""

    def setUp(self):
        self.refund_pipe = RefundPayPalPayment("test_pipe", None)
        self.order_id = "mock_order_id"
        self.amount_in_cents = 1000
        self.ct_transaction_interaction_id = "mock_capture_id"
        self.psp = EDX_PAYPAL_PAYMENT_INTERFACE_NAME

    @patch('commerce_coordinator.apps.paypal.clients.PayPalClient.refund_order')
    def test_refund_successful(self, mock_refund_order):
        """Test successful PayPal refund"""
        mock_refund_order.return_value = {"status": "COMPLETED"}

        ret = self.refund_pipe.run_filter(
            order_id=self.order_id,
            amount_in_cents=self.amount_in_cents,
            has_been_refunded=False,
            ct_transaction_interaction_id=self.ct_transaction_interaction_id,
            psp=self.psp,
            message_id="mock_message_id"
        )

        self.assertEqual(ret['refund_response'], {"status": "COMPLETED"})
        mock_refund_order.assert_called_once_with(capture_id=self.ct_transaction_interaction_id,
                                                  amount=self.amount_in_cents)

    def test_refund_already_refunded(self):
        """Test refund when payment has already been refunded"""
        ret = self.refund_pipe.run_filter(
            order_id=self.order_id,
            amount_in_cents=self.amount_in_cents,
            has_been_refunded=True,
            ct_transaction_interaction_id=self.ct_transaction_interaction_id,
            psp=self.psp
        )

        self.assertEqual(ret['refund_response'], "charge_already_refunded")

    def test_refund_invalid_psp(self):
        """Test refund with invalid PSP"""
        ret = self.refund_pipe.run_filter(
            order_id=self.order_id,
            amount_in_cents=self.amount_in_cents,
            has_been_refunded=False,
            ct_transaction_interaction_id=self.ct_transaction_interaction_id,
            psp="invalid_psp"
        )

        self.assertEqual(ret, PipelineCommand.CONTINUE.value)

    def test_refund_missing_amount_or_capture_id(self):
        """Test refund with missing amount or capture ID"""
        ret = self.refund_pipe.run_filter(
            order_id=self.order_id,
            amount_in_cents=None,
            has_been_refunded=False,
            ct_transaction_interaction_id=self.ct_transaction_interaction_id,
            psp=self.psp
        )

        self.assertEqual(ret, PipelineCommand.CONTINUE.value)

        ret = self.refund_pipe.run_filter(
            order_id=self.order_id,
            amount_in_cents=self.amount_in_cents,
            has_been_refunded=False,
            ct_transaction_interaction_id=None,
            psp=self.psp
        )

        self.assertEqual(ret, PipelineCommand.CONTINUE.value)

    @patch('commerce_coordinator.apps.paypal.clients.PayPalClient.refund_order')
    def test_refund_exception(self, mock_refund_order):
        """Test refund with exception raised"""
        mock_refund_order.side_effect = Exception("mock exception")

        ret = self.refund_pipe.run_filter(
            order_id=self.order_id,
            amount_in_cents=self.amount_in_cents,
            has_been_refunded=False,
            ct_transaction_interaction_id=self.ct_transaction_interaction_id,
            psp=self.psp,
            message_id="mock_message_id"
        )
        self.assertEqual(ret['psp_refund_error'], "mock exception")
