"""Tests for the commercetools views"""

import ddt
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from commerce_coordinator.apps.core.tests.utils import name_test


@ddt.ddt
class OrderFulfillViewTests(APITestCase):
    "Tests for order fulfill view"
    url = reverse('commercetools:fulfill')

    @ddt.data(
        name_test("test success", (
            {}, None, status.HTTP_200_OK,
            {}
        )),
        name_test("test no details", (
            {}, 'detail', status.HTTP_400_BAD_REQUEST,
            {'error_key': 'detail', 'error_message': 'This field is required.'}
        ))
    )
    @ddt.unpack
    def test_fulfill_view(self, update_params, skip_params, expected_status, expected_error):
        message = {
            'version': '0',
            'id': 'aaaaaaaa-8888-00ee-aaaa-aaaaaaaaaaaa',
            'detail-type': 'OrderStateChanged',
            'source': 'aws.partner/commercetools.com/2u-marketplace-dev-01/commerce-coordinator-eventbridge',
            'account': '835688427423',
            'time': '2023-11-21T13:21:11Z',
            'region': 'us-east-2',
            'resources': [],
            'detail': {
                'notificationType': 'Message',
                'projectKey': '2u-marketplace-dev-01',
                'id': '3cbbbbbb-ce15-4979-aaca-bb121bbbbbbb',
                'version': 1,
                'sequenceNumber': 57,
                'resource': {
                    'typeId': 'order',
                    'id': '9e60e10b-861c-40b0-afa4-c769dcccccc1'
                },
                'resourceVersion': 58,
                'type': 'OrderStateChanged',
                'orderId': '9e60e10b-861c-40b0-afa4-c769dcccccc1',
                'orderState': 'Complete',
                'oldOrderState': 'Cancelled',
                'createdAt': '2023-11-21T13:21:11.122Z',
                'lastModifiedAt': '2023-11-21T13:21:11.122Z',
                'createdBy': {
                    'isPlatformClient': True,
                    'user': {
                        'typeId': 'user',
                        'id': '5daf67fd-15a6-4d77-9149-01413dddddd3'
                    },
                },
                'lastModifiedBy': {
                    'isPlatformClient': True,
                    'user': {
                        'typeId': 'user',
                        'id': '5daf67fd-15a6-4d77-9149-01413dddddd3'
                    },
                },
            },
        }

        message.update(update_params)

        if skip_params:
            del message[skip_params]

        response = self.client.post(self.url, data=message, format="json")
        self.assertEqual(response.status_code, expected_status)
        if expected_status != status.HTTP_200_OK:
            response_json = response.json()
            expected_error_key = expected_error['error_key']
            expected_error_message = expected_error['error_message']
            self.assertIn(expected_error_key, response_json)
            self.assertIn(expected_error_message, response_json[expected_error_key])

# """ Commercetools Order History testcases """
# from unittest.mock import MagicMock, patch
#
# from django.contrib.auth import get_user_model
# from django.urls import reverse
# from rest_framework.test import APITestCase
#
# from commerce_coordinator.apps.commercetools.clients import PaginatedResult
# from commerce_coordinator.apps.commercetools.tests.conftest import gen_order
# from commerce_coordinator.apps.commercetools.tests.test_data import gen_customer
# from commerce_coordinator.apps.core.tests.utils import uuid4_str
# from commerce_coordinator.apps.frontend_app_ecommerce.tests.test_views import EcommerceClientMock
#
# User = get_user_model()
#
# orders = [gen_order(uuid4_str())]
#
#
# class CTOrdersForCustomerMock(MagicMock):
#     """A mock EcommerceAPIClient that always returns ECOMMERCE_REQUEST_EXPECTED_RESPONSE."""
#     return_value = (
#         PaginatedResult(orders, len(orders), 0),
#         gen_customer(email='test@example.com', un="test")
#     )
#
#
# class OrderHistoryViewTests(APITestCase):
#     """
#     Tests for order history view
#     """
#
#     # Define test user properties
#     test_user_username = 'test'
#     test_user_email = 'test@example.com'
#     test_user_password = 'secret'
#     url = reverse('commercetools:order_history')
#
#     def setUp(self):
#         """Create test user before test starts."""
#         super().setUp()
#         self.user = User.objects.create_user(
#             self.test_user_username,
#             self.test_user_email,
#             self.test_user_password,
#             lms_user_id=127,
#             # TODO: Remove is_staff=True
#             is_staff=True,
#         )
#
#     def tearDown(self):
#         """Log out any user from the client after test ends."""
#         super().tearDown()
#         self.client.logout()
#
#     @patch(
#         'commerce_coordinator.apps.ecommerce.clients.EcommerceAPIClient.get_orders',
#         new_callable=EcommerceClientMock
#     )
#     @patch(
#         'commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_orders_for_customer',
#         new_callable=CTOrdersForCustomerMock
#     )
#     def test_order_history_functional(self, _, __):
#         """Happy path test function for CT Order History"""
#         self.client.force_authenticate(user=self.user)
#         query_params = {}  # we don't accept any rn
#
#         response = self.client.get(self.url, data=query_params)
#         self.assertEqual(response.status_code, 200)
#
#         response_json: dict = response.json()
#
#         self.assertIn('order_data', response_json.keys())
#         self.assertEqual(2, len(response_json['order_data']))
#         # because of how the dates work within this test the old system value should be second as its date is older
#         self.assertEqual(response_json['order_data'][1]['payment_processor'], 'cybersource-rest')
#
#     def test_order_history_denied(self):
#         """bad/incomplete auth test function for CT Order History"""
#
#         self.client.force_authenticate(user=User.objects.create_user(
#                 "joey",
#                 "something@something.com",
#                 "shh its @ secret!",
#                 # TODO: Remove is_staff=True
#                 is_staff=True,
#             ))
#         query_params = {}  # we don't accept any rn
#
#         response = self.client.get(self.url, data=query_params)
#         self.assertEqual(response.status_code, 403)
#
#         self.client.logout()
