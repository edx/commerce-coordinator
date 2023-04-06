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
CONTENT_TYPE = 'application/vnd.api+json'
LOGGER_NAME = 'commerce_coordinator.apps.titan.clients'
TITAN_API_KEY = 'top-secret'


@ddt.ddt
@override_settings(TITAN_URL=TITAN_URL)
@override_settings(TITAN_API_KEY=TITAN_API_KEY)
class TestTitanAPIClient(TestCase):
    """TitanAPIClient tests."""
    def setUp(self) -> None:
        self.client = TitanAPIClient()
        self.order_uuid = 'test-uuid'
        self.order_create_data = {
            'edx_lms_user_id': 1,
            'email': 'edx@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
        }
        self.add_item_data = {
            'order_uuid': self.order_uuid,
            'course_sku': 'test-sku',
        }
        self.order_complete_data = {
            'order_uuid': self.order_uuid,
            'edx_lms_user_id': 1,
        }

    def _mock_create_order(self, status=200):
        """Does required mocking for create order API"""
        url = urljoin(TITAN_URL, 'edx/api/v1/cart')
        body = json.dumps(
            {
                'uuid': self.order_uuid,
            }
        )
        responses.add(responses.POST, url, body=body, content_type=CONTENT_TYPE, status=status)

    def _assert_request_headers(self, headers):
        self.assertEqual(headers['X-Spree-API-Key'], TITAN_API_KEY)
        self.assertEqual(headers['Content-Type'], CONTENT_TYPE)

    def _assert_order_create_request(self, request):
        """Assert request."""
        self._assert_request_headers(request.headers)
        request_body = json.loads(request.body)['data']['attributes']
        self.assertEqual(request_body['currency'], 'USD')
        self.assertEqual(request_body['edxLmsUserId'], self.order_create_data['edx_lms_user_id'])
        self.assertEqual(request_body['email'], self.order_create_data['email'])
        self.assertEqual(request_body['firstName'], self.order_create_data['first_name'])
        self.assertEqual(request_body['lastName'], self.order_create_data['last_name'])

    @responses.activate
    def test_order_create_success(self):
        self._mock_create_order()
        with LogCapture(LOGGER_NAME) as logger:
            response = self.client.create_order(**self.order_create_data)
            logger.check_present(
                (LOGGER_NAME, 'DEBUG', 'Response status: 200 OK'),
            )
        self.assertEqual(response['uuid'], self.order_uuid)
        request = responses.calls[-1].request
        self._assert_order_create_request(request)

    @responses.activate
    def test_order_create_failure(self):
        self._mock_create_order(status=400)
        with LogCapture(LOGGER_NAME) as logger:
            with pytest.raises(HTTPError):
                self.client.create_order(**self.order_create_data)
            logger.check_present(
                (LOGGER_NAME, 'INFO', 'Response status: 400 Bad Request'),
            )
        request = responses.calls[-1].request
        self._assert_order_create_request(request)

    def _mock_add_item(self, status=200):
        """add required mocking for add_item API"""
        url = urljoin(TITAN_URL, 'edx/api/v1/cart/add_item')
        body = json.dumps(
            {
                'uuid': self.order_uuid,
            }
        )
        responses.add(responses.POST, url, body=body, content_type=CONTENT_TYPE, status=status)

    def _assert_add_item_request(self, request):
        self._assert_request_headers(request.headers)
        request_body = json.loads(request.body)['data']['attributes']
        self.assertEqual(request_body['orderUuid'], self.add_item_data['order_uuid'])
        self.assertEqual(request_body['courseSku'], self.add_item_data['course_sku'])

    @responses.activate
    def test_add_item_success(self):
        self._mock_add_item()
        with LogCapture(LOGGER_NAME) as logger:
            response = self.client.add_item(**self.add_item_data)
            logger.check_present(
                (LOGGER_NAME, 'DEBUG', 'Response status: 200 OK'),
            )
        self.assertEqual(response['uuid'], self.order_uuid)
        request = responses.calls[-1].request
        self._assert_add_item_request(request)

    @responses.activate
    def test_add_item_failure(self):
        self._mock_add_item(status=400)
        with LogCapture(LOGGER_NAME) as logger:
            with pytest.raises(HTTPError):
                self.client.add_item(**self.add_item_data)
            logger.check_present(
                (LOGGER_NAME, 'INFO', 'Response status: 400 Bad Request'),
            )
        request = responses.calls[-1].request
        self._assert_add_item_request(request)

    def _mock_order_complete(self, status=200):
        """add required mocking for complete API"""
        url = urljoin(TITAN_URL, 'edx/api/v1/checkout/complete')
        body = json.dumps(
            {
                'uuid': self.order_uuid,
            }
        )
        responses.add(responses.POST, url, body=body, content_type=CONTENT_TYPE, status=status)

    def _assert_complete_order_request(self, request):
        self._assert_request_headers(request.headers)
        request_body = json.loads(request.body)['data']['attributes']
        self.assertEqual(request_body['orderUuid'], self.order_complete_data['order_uuid'])
        self.assertEqual(request_body['edxLmsUserId'], self.order_complete_data['edx_lms_user_id'])

    @responses.activate
    def test_order_complete_success(self):
        self._mock_order_complete()
        with LogCapture(LOGGER_NAME) as logger:
            response = self.client.complete_order(**self.order_complete_data)
            logger.check_present(
                (LOGGER_NAME, 'DEBUG', 'Response status: 200 OK'),
            )
        self.assertEqual(response['uuid'], self.order_uuid)
        request = responses.calls[-1].request
        self._assert_complete_order_request(request)

    @responses.activate
    def test_order_complete_failure(self):
        self._mock_order_complete(status=400)
        with LogCapture(LOGGER_NAME) as logger:
            with pytest.raises(HTTPError):
                self.client.complete_order(**self.order_complete_data)
            logger.check_present(
                (LOGGER_NAME, 'INFO', 'Response status: 400 Bad Request'),
            )
        request = responses.calls[-1].request
        self._assert_complete_order_request(request)
