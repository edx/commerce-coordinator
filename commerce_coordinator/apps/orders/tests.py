"""
Tests for the orders app.
"""

import logging

from django.test import TestCase
from django.urls import reverse
from mock import patch

from .clients import EcommerceApiClient


logger = logging.getLogger(__name__)
sample_response = {'count': 1,
                   'results': [{'billing_address': {'city': 'Brighton',
                                                    'country': 'US',
                                                    'first_name': 'Diane',
                                                    'last_name': 'Test',
                                                    'line1': '50 turner st',
                                                    'line2': '',
                                                    'postcode': '02135',
                                                    'state': 'MA'},
                                'currency': 'USD',
                                'date_placed': '2021-12-20T15:09:44Z',
                                'discount': '0',
                                'lines': [{'description': 'Seat in edX                 '
                                            'Demonstration Course with verified '
                                            'certificate (and ID verification)',
                                            'line_price_excl_tax': '149.00',
                                            'product': {'attribute_values': [{'code': 'certificate_type',
                                                                              'name': 'certificate_type',
                                                                              'value': 'verified'},
                                                                             {'code': 'course_key',
                                                                              'name': 'course_key',
                                                                              'value': 'course-v1:\
                                                                                  edX+DemoX+Demo_Course'},
                                                                             {'code': 'id_verification_required',
                                                                              'name': 'id_verification_required',
                                                                              'value': True}],
                                                        'expires': '2022-11-08T22:54:30.777313Z',
                                                        'id': 3,
                                                        'is_available_to_buy': True,
                                                        'price': '149.00',
                                                        'product_class': 'Seat',
                                                        'stockrecords': [{'id': 3,
                                                                          'partner': 1,
                                                                          'partner_sku': '8CF08E5',
                                                                          'price_currency': 'USD',
                                                                          'price_excl_tax': '149.00',
                                                                          'product': 3}],
                                                        'structure': 'child',
                                                        'title': 'Seat in edX Demonstration '
                                                        'Course '
                                                        'with verified certificate (and '
                                                        'ID '
                                                        'verification)',
                                                        'url': 'http://localhost:18130/api/v2/'
                                                        'products/3/'},
                                            'quantity': 1,
                                            'status': 'Complete',
                                            'title': 'Seat in edX Demonstration             '
                                            'Course with verified certificate (and ID '
                                            'verification)',
                                            'unit_price_excl_tax': '149.00'}],
                                'number': 'EDX-100004',
                                'payment_processor': 'cybersource-rest',
                                'status': 'Complete',
                                'total_excl_tax': '149.00',
                                'user': {'email': 'edx@example.com', 'username': 'edx'},
                                'vouchers': []}]}


class OrderRetrievalTests(TestCase):
    """
    Verify endpoint availability for order retrieval endpoint(s)
    """
    maxDiff = None
    ORDER_HISTORY_PATH = reverse('orders:order_history')

    def setUp(self):
        super().setUp()

        class TestResponse:
            def __init__(self, **kwargs):
                self.__dict__ = kwargs

        #  mock response from ecommerce orders API
        self.test_response = TestResponse(**sample_response)

    @patch('commerce_coordinator.apps.orders.clients.EcommerceApiClient.get_orders')
    def test_EcommerceApiClient(self, mock_response):
        """We can call the EcommerceApiClient successfully."""

        mock_response.return_value = self.test_response
        params = {'username': 'TestUser', "page": 1, "page_size": 20}

        # Call the new function (EcommerceApiClient().get_orders(params)), mocking the response
        ecommerce_api_client = EcommerceApiClient()
        ecommerce_response = ecommerce_api_client.get_orders(params)

        self.assertEqual(sample_response, ecommerce_response.__dict__)

    def test_ecommerce_view(self):
        """We can call get_user_orders__ecommerce successfully."""
        test_params = {'username': 'edx', "page": 1, "page_size": 20}
        breakpoint()
        response = self.client.get(self.ORDER_HISTORY_PATH, test_params) #  Invalid URL 'replace-me/oauth2/access_token': No scheme supplied. Perhaps you meant http://replace-me/oauth2/access_token?
        # response = self.client.get('/orders/ecommerce/', test_params) # <HttpResponseNotFound status_code=404, "text/html">
        self.assertEqual(response.status_code, 200)
