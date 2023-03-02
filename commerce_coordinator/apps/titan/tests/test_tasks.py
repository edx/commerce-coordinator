"""Test Titan tasks."""

from django.test import TestCase
from mock.mock import MagicMock, patch

from commerce_coordinator.apps.titan.tasks import create_order_task


class TitanClientMock(MagicMock):
    """A mock EcommerceAPIClient that always returns ECOMMERCE_REQUEST_EXPECTED_RESPONSE."""
    return_value = {
        'spreePaymentId': 12345,
    }


class TestOrderTasks(TestCase):
    """TitanAPIClient tests."""
    order_create_data = {
        'edx_lms_user_id': 1,
        'email': 'edx@example.com',
        'coupon_code': 'test_code',
        'product_sku': ['sku1', 'sku_2']
    }

    @patch('commerce_coordinator.apps.titan.clients.TitanAPIClient.create_order', new_callable=TitanClientMock)
    def test_task(self, __):
        rst = create_order_task.apply(args=(
            self.order_create_data['edx_lms_user_id'],
            self.order_create_data['email'],
            self.order_create_data['product_sku'],
            self.order_create_data['coupon_code'],
        )).get()
        self.assertEqual(rst['spreePaymentId'], 12345)
