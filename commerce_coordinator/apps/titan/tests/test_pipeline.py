""" Titan Pipeline Tests"""

from unittest import TestCase
from unittest.mock import patch

from requests import HTTPError

from commerce_coordinator.apps.titan.pipeline import CreateTitanOrder, GetTitanPayment, GetTitanActiveOrder

from ..exceptions import PaymentNotFound
from .test_clients import ORDER_CREATE_DATA_WITH_CURRENCY, TitanClientMock


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


class TestGetTitanPaymentPipelineStep(TestCase):
    """ A pytest Test Case for then `GetTitanPayment(PipelineStep)` """

    @patch('commerce_coordinator.apps.titan.clients.TitanAPIClient.get_payment', new_callable=TitanClientMock)
    def test_pipeline_step(self, mock_get_payment):
        """
        A test to red/green whether our pipeline step accepts data, invokes right, and sends things off as coded

        Args:
            mock_get_payment(MagicMock): stand in for Titan API Client `get_payment`
        """
        payment_pipe = GetTitanPayment("test_pipe", None)
        get_payment_data = {
            'edx_lms_user_id': 1,
            'payment_number': '1234',
        }

        result: dict = payment_pipe.run_filter(
            **get_payment_data,
        )

        # ensure our input data arrives as expected
        mock_get_payment.assert_called_once_with(**get_payment_data)
        self.assertIn('data', result)

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
            'payment_number': '1234',
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

class TestGetTitanActiveOrderPipelineStep(TestCase):
    """A pytest Test case for the GetTitanActiveOrder Pipeline Step"""
    @patch('commerce_coordinator.apps.titan.clients.TitanAPIClient.get_active_order', new_callable=TitanClientMock)
    def test_pipeline_step(self, mock_get_active_order):
        active_order_pipe = GetTitanActiveOrder("test_pipe", None)
        get_active_order_data = {
            'edx_lms_user_id': 1,
        }
        result: dict = active_order_pipe.run_filter(**get_active_order_data)

        mock_get_active_order.assert_called_once_with(**get_active_order_data)
        self.assertIn('data', result)
