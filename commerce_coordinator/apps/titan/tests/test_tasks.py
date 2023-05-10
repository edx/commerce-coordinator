"""Test Titan tasks."""

from django.test import TestCase
from mock.mock import patch

from commerce_coordinator.apps.titan.tasks import order_created_save_task

from .test_clients import ORDER_CREATE_DATA, ORDER_UUID, TitanClientMock


class TestOrderTasks(TestCase):
    """Titan Order Task, and integration tests."""

    @patch('commerce_coordinator.apps.titan.clients.TitanAPIClient.create_order', new_callable=TitanClientMock)
    def test_task(self, mock_create_order):
        """ Ensure that the `order_created_save_task` invokes create order as expected and has an expected return
            result.

        Args:
            mock_create_order (TitanClientMock): Titan Client Mock for its mock_create_order command.
        """
        order_created_save_task.apply(
            args=ORDER_CREATE_DATA.values()
        ).get()

        mock_create_order.assert_called_with(
            ORDER_CREATE_DATA['product_sku'],
            ORDER_CREATE_DATA['edx_lms_user_id'],
            ORDER_CREATE_DATA['email'],
            ORDER_CREATE_DATA['first_name'],
            ORDER_CREATE_DATA['last_name'],
            ORDER_CREATE_DATA['coupon_code']
        )

        values = mock_create_order.return_value.values()

        # values however should be the value expected as a return from complete_order
        self.assertEqual(list(values), [{'attributes': {'uuid': ORDER_UUID}}])
