'''Constants for commercetools tests'''
from commerce_coordinator.apps.commercetools.catalog_info.constants import TwoUKeys
from commerce_coordinator.apps.commercetools.views import OrderFulfillView

EXAMPLE_COMMERCETOOLS_ORDER_FULFILL_MESSAGE = {
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

EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD = {
    'sender': OrderFulfillView,
    'course_id': 'course-v1:edX+DemoX+Demo_Course',
    'course_mode': 'verified',
    'date_placed': 'Oct 31, 2023',
    'edx_lms_user_id': 127,
    'email_opt_in': True,
    'order_number': 'c1f1961f-7dac-4ec6-a0ff-364b71c082b6',
    'provider_id': None,
    'source_system': 'commercetools',
}

EXAMPLE_COMMERCETOOLS_ORDER_SANCTIONED_MESSAGE = {
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
        'orderState': TwoUKeys.SDN_SANCTIONED_ORDER_STATE,
        'oldOrderState': 'Open',
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
