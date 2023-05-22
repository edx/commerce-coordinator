""" Titan Pipeline Tests"""

from unittest import TestCase
from unittest.mock import patch

from commerce_coordinator.apps.titan.pipeline import CreateTitanOrder

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
