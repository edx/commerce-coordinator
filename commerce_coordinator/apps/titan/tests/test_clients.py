"""Test Titan clients."""

import json
from urllib.parse import urljoin

import ddt
import pytest
import responses
from django.test import TestCase, override_settings
from requests import HTTPError
from testfixtures import LogCapture

from commerce_coordinator.apps.titan.clients import TitanAPIClient

TITAN_URL = 'https://testserver.com'
CONTENT_TYPE = 'application/json'
LOGGER_NAME = 'commerce_coordinator.apps.titan.clients'


@ddt.ddt
@override_settings(TITAN_URL=TITAN_URL)
class TestTitanAPIClient(TestCase):
    """TitanAPIClient tests."""
    def setUp(self) -> None:
        self.client = TitanAPIClient()
        self.order_create_data = {
            'edx_lms_user_id': 1,
            'email': 'edx@example.com',
            'coupon_code': 'test_code',
            'product_sku': ['sku1', 'sku_2']
        }

    def _mock_create_order(self, status=200):
        """Does required mocking for create order API"""
        url = urljoin(TITAN_URL, '/v1/order')
        body = json.dumps(
            {
                'spreePaymentId': 12345,
            }
        )
        responses.add(responses.PUT, url, body=body, content_type=CONTENT_TYPE, status=status)

    @responses.activate
    def test_order_create_success(self):
        self._mock_create_order()
        with LogCapture(LOGGER_NAME) as logger:
            response = self.client.create_order(**self.order_create_data)
            logger.check_present(
                (LOGGER_NAME, 'DEBUG', 'response status: 200'),
            )
            self.assertEqual(response['spreePaymentId'], 12345)

    @responses.activate
    def test_order_create_failure(self):
        self._mock_create_order(status=400)
        with LogCapture(LOGGER_NAME) as logger:
            with pytest.raises(HTTPError):
                self.client.create_order(**self.order_create_data)
            logger.check_present(
                (LOGGER_NAME, 'DEBUG', 'response status: 400'),
            )
