"""Tests for the commercetools views"""

import ddt
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from commerce_coordinator.apps.core.tests.utils import name_test


@ddt.ddt
class OrderFulfillViewTests(APITestCase):

    url = reverse('commercetools:fulfill')

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    @ddt.data(
        name_test("test success", (
            {}, None, status.HTTP_200_OK,
            {}
        )),
        name_test("test no details", (
            {}, 'detail', status.HTTP_400_BAD_REQUEST,
            {'error_key': 'detail', 'error_message': 'This field may not be null.'}
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
