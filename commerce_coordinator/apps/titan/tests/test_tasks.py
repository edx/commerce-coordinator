"""Test Titan tasks."""

from django.test import TestCase
from mock.mock import MagicMock, patch

from commerce_coordinator.apps.titan.tasks import order_created_save_task

ORDER_UUID = 'test-uuid'


class TitanClientMock(MagicMock):
    """A mock EcommerceAPIClient that always returns ECOMMERCE_REQUEST_EXPECTED_RESPONSE."""
    return_value = {
        'uuid': ORDER_UUID,
    }


class TestOrderTasks(TestCase):
    """TitanAPIClient tests."""
    order_create_data = {
        'product_sku': ['sku1', 'sku_2'],
        'edx_lms_user_id': 1,
        'email': 'edx@example.com',
        'first_name': 'John',
        'last_name': 'Doe',
        'coupon_code': 'test_code',
    }

    @patch('commerce_coordinator.apps.titan.clients.TitanAPIClient.create_order', new_callable=TitanClientMock)
    @patch('commerce_coordinator.apps.titan.clients.TitanAPIClient.add_item', new_callable=TitanClientMock)
    @patch('commerce_coordinator.apps.titan.clients.TitanAPIClient.complete_order', new_callable=TitanClientMock)
    def test_task(self, mock_complete_order, mock_add_item, mock_create_order):
        order_created_save_task.apply(
            args=self.order_create_data.values()
        ).get()
        mock_create_order.assert_called_with(
            self.order_create_data['edx_lms_user_id'],
            self.order_create_data['email'],
            self.order_create_data['first_name'],
            self.order_create_data['last_name'],
        )
        mock_add_item.assert_called_with(
            ORDER_UUID, self.order_create_data['product_sku'][-1]
        )
        mock_complete_order.assert_called_with(
            ORDER_UUID, self.order_create_data['edx_lms_user_id']
        )
