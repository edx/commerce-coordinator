"""
Tests for the orders app.
"""

import logging

from django.test import TestCase
from mock import patch

from .clients import EcommerceApiClient

logger = logging.getLogger(__name__)


class OrderRetrievalTests(TestCase):
    """
    Verify endpoint availability for order retrieval endpoint(s)
    """
    maxDiff = None

    def setUp(self):
        super().setUp()

        class TestResponse:
            def __init__(self, **kwargs):
                self.__dict__ = kwargs

        #  mock response from ecommerce orders API
        self.test_response = TestResponse(**{
            'count': 1,
            'results': [{"billing_address": {"first_name": "Diane", "last_name": "Test", "line1": "50 turner st", "line2": "", "postcode": "02135", "state": "MA", "country": "US", "city": "Brighton"}, "currency": "USD", "date_placed": "2021-12-20T15:09:44Z", "discount": "0", "lines": [{"title": "Seat in edX Demonstration Course with verified certificate (and ID verification)", "quantity": 1, "description": "Seat in edX Demonstration Course with verified certificate (and ID verification)", "status": "Complete", "line_price_excl_tax": "149.00", "unit_price_excl_tax": "149.00", "product": {"id": 3, "url": "http://localhost:18130/api/v2/products/3/", "structure": "child", "product_class": "Seat", "title": "Seat in edX Demonstration Course with verified certificate (and ID verification)", "price": "149.00", "expires": "2022-11-08T22:54:30.777313Z", "attribute_values": [{"name": "certificate_type", "code": "certificate_type", "value": "verified"}, {"name": "course_key", "code": "course_key", "value": "course-v1:edX+DemoX+Demo_Course"}, {"name": "id_verification_required", "code": "id_verification_required", "value": True}], "is_available_to_buy": True, "stockrecords": [{"id": 3, "product": 3, "partner": 1, "partner_sku": "8CF08E5", "price_currency": "USD", "price_excl_tax": "149.00"}]}}], "number": "EDX-100004", "payment_processor": "cybersource-rest", "status": "Complete", "total_excl_tax": "149.00", "user": {"email": "edx@example.com", "username": "edx"}, "vouchers": []}]  # pylint: disable=line-too-long  # nopep8
        })

    @patch('commerce_coordinator.apps.orders.clients.EcommerceApiClient.get_orders')
    def test_ecommerce_view(self, mock_response):
        """We can call get_user_orders__ecommerce successfully."""

        mock_response.return_value = self.test_response
        params = {'username': 'TestUser', "page": 1, "page_size": 20}
        expected_result = {'count': 1, 'results': [{"billing_address": {"first_name": "Diane", "last_name": "Test", "line1": "50 turner st", "line2": "", "postcode": "02135", "state": "MA", "country": "US", "city": "Brighton"}, "currency": "USD", "date_placed": "2021-12-20T15:09:44Z", "discount": "0", "lines": [{"title": "Seat in edX Demonstration Course with verified certificate (and ID verification)", "quantity": 1, "description": "Seat in edX Demonstration Course with verified certificate (and ID verification)", "status": "Complete", "line_price_excl_tax": "149.00", "unit_price_excl_tax": "149.00", "product": {"id": 3, "url": "http://localhost:18130/api/v2/products/3/", "structure": "child", "product_class": "Seat", "title": "Seat in edX Demonstration Course with verified certificate (and ID verification)", "price": "149.00", "expires": "2022-11-08T22:54:30.777313Z", "attribute_values": [{"name": "certificate_type", "code": "certificate_type", "value": "verified"}, {"name": "course_key", "code": "course_key", "value": "course-v1:edX+DemoX+Demo_Course"}, {"name": "id_verification_required", "code": "id_verification_required", "value": True}], "is_available_to_buy": True, "stockrecords": [{"id": 3, "product": 3, "partner": 1, "partner_sku": "8CF08E5", "price_currency": "USD", "price_excl_tax": "149.00"}]}}], "number": "EDX-100004", "payment_processor": "cybersource-rest", "status": "Complete", "total_excl_tax": "149.00", "user": {"email": "edx@example.com", "username": "edx"}, "vouchers": []}]}  # pylint: disable=line-too-long  # nopep8

        # Call the new function (get_user_orders__ecommerce), mocking the call to ecommerce_api_client.get_orders
        ecommerce_api_client = EcommerceApiClient()
        ecommerce_response = ecommerce_api_client.get_orders(params)

        self.assertEqual(expected_result, ecommerce_response.__dict__)
