""" Titan Pipeline Tests"""

from unittest import TestCase
from unittest.mock import patch

import ddt
from requests import HTTPError
from rest_framework.exceptions import APIException

from commerce_coordinator.apps.titan.pipeline import (
    CreateDraftPayment,
    CreateTitanOrder,
    GetTitanActiveOrder,
    GetTitanPayment,
    UpdateBillingAddress,
    UpdateTitanPayment,
    ValidatePaymentReadyForProcessing
)

from ...core.constants import PaymentMethod, PaymentState
from ..exceptions import (
    AlreadyPaid,
    InvalidOrderPayment,
    NoActiveOrder,
    PaymentMismatch,
    PaymentNotFound,
    ProcessingAlreadyRequested
)
from .test_clients import (
    ORDER_CREATE_DATA_WITH_CURRENCY,
    ORDER_UUID,
    TitanActiveOrderClientMock,
    TitanClientMock,
    TitanPaymentClientMock,
    titan_active_order_response
)


class TestCreateTitanOrderPipelineStep(TestCase):
    """ A pytest Test Case for then `CreateTitanOrder(PipelineStep)` """

    @patch('commerce_coordinator.apps.titan.clients.TitanAPIClient.create_order', new_callable=TitanClientMock)
    def test_pipeline_step_independently(self, mock_create_order):
        """
        A test to red/green whether our pipeline step accepts data, invokes right, and sends things off as coded

        Args:
            mock_create_order(MagicMock): standin for Titan API Client `create_order`
        """
        order = CreateTitanOrder("test", None)
        extra_order_data = 'order_detail_extra_val'
        input_order_data = ORDER_CREATE_DATA_WITH_CURRENCY

        result: dict = order.run_filter(
            input_order_data,
            [extra_order_data]
        )

        # ensure our input data arrives as expected
        mock_create_order.assert_called_once_with(**input_order_data)

        self.assertIn('order_data', result)

        order_data: list = result['order_data']
        self.assertEqual(2, len(order_data))

        self.assertIn(extra_order_data, order_data)

        order_data.remove(extra_order_data)

        input_web_response_order_data = order_data[-1]

        # Technically this isn't "order data" but the response to create order which is an order uuid.
        self.assertEqual(TitanClientMock.return_value, input_web_response_order_data)


@ddt.ddt
class TestGetTitanPaymentPipelineStep(TestCase):
    """ A pytest Test Case for then `GetTitanPayment(PipelineStep)` """

    def setUp(self) -> None:
        self.payment_pipe = GetTitanPayment("test_pipe", None)

    @patch('commerce_coordinator.apps.titan.clients.TitanAPIClient.get_payment', new_callable=TitanPaymentClientMock)
    def test_pipeline_step(self, mock_get_payment):
        """
        A test to red/green whether our pipeline step accepts data, invokes right, and sends things off as coded

        Args:
            mock_get_payment(MagicMock): stand in for Titan API Client `get_payment`
        """
        get_payment_data = {
            'edx_lms_user_id': 1,
        }

        result: dict = self.payment_pipe.run_filter(
            **get_payment_data,
        )['payment_data']

        # ensure our input data arrives as expected
        mock_get_payment.assert_called_once_with(**get_payment_data)
        self.assertIn('payment_number', result)
        self.assertIn('order_uuid', result)
        self.assertIn('key_id', result)
        self.assertIn('state', result)

    @patch('commerce_coordinator.apps.titan.clients.TitanAPIClient.get_payment',  new_callable=TitanPaymentClientMock)
    def test_get_payment_order_mismatch(self, __):
        """
        Ensure data validation if we try to send wrong Order ID that does not belong to that payment.
        """
        query_params = {
            # this order id is different form what we will get from titan
            'edx_lms_user_id': 1,
            'order_uuid': '321e7654-e89b-12d3-a456-426614174111',
        }

        with self.assertRaises(InvalidOrderPayment) as ex:
            self.payment_pipe.run_filter(
                **query_params,
            )

        self.assertEqual(
            str(ex.exception),
            'Requested order_uuid "321e7654-e89b-12d3-a456-426614174111" does not match '
            'with order_uuid "123e4567-e89b-12d3-a456-426614174000" in Spree system.'
        )

    @patch('commerce_coordinator.apps.titan.clients.TitanAPIClient.get_payment',  new_callable=TitanPaymentClientMock)
    def test_get_payment_mismatch(self, __):
        """
        Ensure data validation if we try to send wrong Order ID that does not belong to that payment.
        """
        query_params = {
            # this payment_number is different form what we will get from titan
            'edx_lms_user_id': 1,
            'payment_number': 'an-other-payment-number',
        }

        with self.assertRaises(PaymentMismatch) as ex:
            self.payment_pipe.run_filter(
                **query_params,
            )

        self.assertEqual(
            str(ex.exception),
            'Requested payment number "an-other-payment-number" does not match '
            'with payment number "test-number" in Spree system.'
        )

    @patch('commerce_coordinator.apps.titan.clients.TitanAPIClient.get_payment', side_effect=HTTPError)
    def test_pipeline_step_raises_exception(self, mock_get_payment):
        """
        A test to red/green whether our pipeline step accepts data, invokes right, and sends things off as coded

        Args:
            mock_get_payment(MagicMock): stand in for Titan API Client `get_payment`
        """
        payment_pipe = GetTitanPayment("test_pipe", None)
        get_payment_data = {
            'edx_lms_user_id': 1,
        }

        with self.assertRaises(PaymentNotFound) as ex:
            payment_pipe.run_filter(
                **get_payment_data,
            )

        self.assertEqual(
            str(ex.exception),
            'Requested payment not found. Please make sure you are passing active payment number.'
        )
        # ensure our input data arrives as expected
        mock_get_payment.assert_called_once_with(**get_payment_data)


@ddt.ddt
class TestValidatePaymentReadyForProcessingStep(TestCase):
    """ A pytest Test Case for then `ValidatePaymentReadyForProcessing(PipelineStep)` """

    def setUp(self) -> None:
        self.validate_payment_pipe = ValidatePaymentReadyForProcessing("test_pipe", None)

    @ddt.data(
        (
            PaymentState.PENDING.value,
            ProcessingAlreadyRequested,
            'Requested payment "test-number" for processing is already processing.'
        ),
        (
            PaymentState.COMPLETED.value,
            AlreadyPaid,
            'Requested payment "test-number" for processing is already paid.'
        ),
        (
            PaymentState.CHECKOUT.value, None, None
        ),
        (
            PaymentState.FAILED.value, None, None
        ),
        (
            PaymentState.PROCESSING.value, None, None
        ),
    )
    @ddt.unpack
    @patch('commerce_coordinator.apps.titan.clients.TitanAPIClient.get_payment')
    def test_get_payment_validate_processing(self, payment_state, expected_error, expected_mesg, mock_get_payment):
        """
        Ensure data validation if we try to send wrong Order ID that does not belong to that payment.
        """
        payment = {**TitanPaymentClientMock.return_value, 'state': payment_state}
        mock_get_payment.return_value = payment
        query_params = {
            'payment_data': payment,
            'payment_number': 'test-number',
        }

        if expected_error:
            with self.assertRaises(expected_error) as ex:
                self.validate_payment_pipe.run_filter(
                    **query_params,
                )

            self.assertEqual(
                str(ex.exception),
                expected_mesg
            )
        else:
            result = self.validate_payment_pipe.run_filter(
                **query_params,
            )
            self.assertIn('payment_data', result)


class TestGetTitanActiveOrderPipelineStep(TestCase):
    """A pytest Test case for the GetTitanActiveOrder Pipeline Step"""
    @patch('commerce_coordinator.apps.titan.clients.TitanAPIClient.get_active_order',
           new_callable=TitanActiveOrderClientMock)
    def test_pipeline_step(self, mock_get_active_order):
        active_order_pipe = GetTitanActiveOrder("test_pipe", None)
        get_active_order_data = {
            'edx_lms_user_id': 1,
        }
        result: dict = active_order_pipe.run_filter(**get_active_order_data)

        mock_get_active_order.assert_called_once_with(**get_active_order_data)
        self.assertIn('basket_id', result.get('order_data'))

    @patch('commerce_coordinator.apps.titan.clients.TitanAPIClient.get_active_order', side_effect=HTTPError)
    def test_pipeline_step_raises_exception(self, mock_get_active_order):
        active_order_pipe = GetTitanActiveOrder("test_pipe", None)
        get_active_order_data = {
            'edx_lms_user_id': 1,
        }
        with self.assertRaises(NoActiveOrder) as ex:
            active_order_pipe.run_filter(
                **get_active_order_data,
            )

        self.assertEqual(
            str(ex.exception),
            'The user with the specified edx_lms_user_id does not have an active order'
        )
        # ensure our input data arrives as expected
        mock_get_active_order.assert_called_once_with(**get_active_order_data)


class TestCreateDraftPaymentStep(TestCase):
    """A pytest Test case for the CreateDraftPayment Pipeline Step"""

    def setUp(self) -> None:
        self.create_payment_data = {
            'order_uuid': ORDER_UUID,
            'response_code': 'test_code',
            'payment_method_name': PaymentMethod.STRIPE.value,
            'provider_response_body': {},
        }

    @patch('commerce_coordinator.apps.titan.clients.TitanAPIClient.create_payment')
    def test_pipeline_step(self, mock_create_payment):
        """
        Test success.
        """
        mock_create_payment.return_value = titan_active_order_response['payments'][0]
        create_draft_payment_pipe = CreateDraftPayment("test_pipe", None)
        result: dict = create_draft_payment_pipe.run_filter(**self.create_payment_data)

        mock_create_payment.assert_called_once_with(**self.create_payment_data)
        self.assertIn('key_id', result)

    @patch('commerce_coordinator.apps.titan.clients.TitanAPIClient.create_payment', side_effect=HTTPError)
    def test_pipeline_step_raises_exception(self, mock_create_payment):
        active_order_pipe = CreateDraftPayment("test_pipe", None)
        with self.assertRaises(APIException) as ex:
            active_order_pipe.run_filter(
                **self.create_payment_data,
            )

        self.assertEqual(
            str(ex.exception),
            "Error while creating payment on titan's system"
        )
        # ensure our input data arrives as expected
        mock_create_payment.assert_called()


class TestUpdateBillingAddressStep(TestCase):
    """A pytest Test case for the UpdateBillinAddress Pipeline Step"""

    def setUp(self) -> None:
        self.billing_details_data = {
            'address1': 'test address',
            'address2': '1',
            'city': 'a place',
            'company': 'a company',
            'countryIso': 'US',
            'firstName': 'test',
            'lastName': 'mctester',
            'phone': '5558675309',
            'stateName': 'MA',
            'zipcode': '55555',
        }

    @patch('commerce_coordinator.apps.titan.clients.TitanAPIClient.update_billing_address')
    def test_pipeline_step(self, mock_update_billing_address):
        update_billing_address_pipe = UpdateBillingAddress("test_pipe", None)
        mock_update_billing_address.return_value = self.billing_details_data
        result: dict = update_billing_address_pipe.run_filter(
            ORDER_UUID,
            **self.billing_details_data,
        )
        result_data = result['billing_address_data']
        self.assertIn('address_1', result_data)
        self.assertEqual(result_data['address_1'], 'test address')

    @patch('commerce_coordinator.apps.titan.clients.TitanAPIClient.update_billing_address', side_effect=HTTPError)
    def test_pipeline_step_with_exception(self, mock_update_billing_address):
        update_billing_address_pipe = UpdateBillingAddress("test_pipe", None)
        mock_update_billing_address.return_value = self.billing_details_data
        with self.assertRaises(APIException) as exc:
            update_billing_address_pipe.run_filter(
                ORDER_UUID,
                **self.billing_details_data,
            )
        self.assertEqual(
            str(exc.exception),
            "Error updating the order's billing address details in titan"
        )
        # ensure our input data arrives as expected
        mock_update_billing_address.assert_called()


class TestUpdateTitanPaymentStep(TestCase):
    """A pytest Test case for the UpdateTitanPayment Pipeline Step"""

    def setUp(self) -> None:
        self.update_payment_data = {
            'payment_number': '1234',
            'payment_state': PaymentState.PROCESSING.value,
            'response_code': 'a_stripe_response_code',
        }
        self.update_payment_response = {
            'number': '1234',
            'orderUuid': ORDER_UUID,
            'responseCode': 'a_stripe_response_code',
            'state': PaymentState.PROCESSING.value,
        }

    @patch('commerce_coordinator.apps.titan.clients.TitanAPIClient.update_payment')
    def test_pipeline_step(self, mock_update_payment):
        update_payment_pipe = UpdateTitanPayment("test_pipe", None)
        mock_update_payment.return_value = self.update_payment_response
        result: dict = update_payment_pipe.run_filter(
            **self.update_payment_data,
        )
        result_data = result['payment_data']
        self.assertIn('order_uuid', result_data)
        self.assertEqual(result_data['order_uuid'], ORDER_UUID)

    @patch('commerce_coordinator.apps.titan.clients.TitanAPIClient.update_payment', side_effect=HTTPError)
    def test_pipeline_step_with_exception(self, mock_update_payment):
        update_payment_pipe = UpdateTitanPayment("test_pipe", None)
        mock_update_payment.return_value = self.update_payment_response
        with self.assertRaises(APIException) as exc:
            update_payment_pipe.run_filter(
                **self.update_payment_data,
            )
        self.assertEqual(
            str(exc.exception),
            "Error updating the payment details in titan"
        )
        # ensure our input data arrives as expected
        mock_update_payment.assert_called()
