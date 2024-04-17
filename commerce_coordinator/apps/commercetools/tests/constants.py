'''Constants for commercetools tests'''
from commerce_coordinator.apps.commercetools.catalog_info.constants import TwoUKeys
from commerce_coordinator.apps.commercetools.views import OrderFulfillView

EXAMPLE_COMMERCETOOLS_ORDER_FULFILL_MESSAGE = {
    'version': '0',
    'id': 'e23aa944-1937-5111-ca7f-aa651920234e',
    'detail-type': 'LineItemStateTransition',
    'source': 'aws.partner/commercetools.com/2u-marketplace-dev-01/commerce-coordinator-eventbridge',
    'account': '838788427423',
    'time': '2024-03-26T11:13:26Z',
    'region': 'us-east-1',
    'resources': [],
    'detail': {
        'notificationType': 'Message',
        'projectKey': '2u-marketplace-dev-01',
        'id': '1bbcda40-a137-413a-b4a1-675f981bc5fc',
        'version': 1,
        'sequenceNumber': 5,
        'resource': {
            'typeId': 'order',
            'id': '61ec1afa-1b0e-4234-ae28-f997728054fa'
        },
        'resourceVersion': 5,
        'resourceUserProvidedIdentifiers': {
            'orderNumber': 'c1f1961f-7dac-4ec6-a0ff-364b71c082b6'
        },
        'type': 'LineItemStateTransition',
        'lineItemId': '822d77c4-00a6-4fb9-909b-094ef0b8c4b9',
        'transitionDate': '2024-03-26T11:13:26.638Z',
        'quantity': 2,
        'fromState': {
            'typeId': 'state',
            'id': '8f2e888e-9777-4557-9a7f-c649153770c2'
        },
        'toState': {
            'typeId': 'state',
            'id': '669d3d11-5eaa-4521-b146-ccbd408ae940'
        },
        'createdAt': '2024-03-26T11:13:26.646Z',
        'lastModifiedAt': '2024-03-26T11:13:26.646Z',
        'createdBy': {
            'isPlatformClient': True,
            'user': {
                'typeId': 'user',
                'id': 'e4713035-68c7-457d-882b-61615caefae2'
            }
        },
        'lastModifiedBy': {
            'isPlatformClient': True,
            'user': {
                'typeId': 'user',
                'id': 'e4713035-68c7-457d-882b-61615caefae2'
            }
        }
    }
}

EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD = {
    'sender': OrderFulfillView,
    'course_id': 'course-v1:MichiganX+InjuryPreventionX+1T2021',
    'course_mode': 'verified',
    'date_placed': 'Oct 31, 2023',
    'email_opt_in': True,
    'line_item_id': '822d77c4-00a6-4fb9-909b-094ef0b8c4b9',
    'item_quantity': 1,
    'order_number': '61ec1afa-1b0e-4234-ae28-f997728054fa',
    'order_version': '7',
    'provider_id': None,
    'source_system': 'commercetools',
    'line_item_state_id': '8f2e888e-9777-4557-9a7f-c649153770c2',
    'edx_lms_user_id': 127,
}

EXAMPLE_UPDATE_LINE_ITEM_SIGNAL_PAYLOAD = {
    'order_id': '61ec1afa-1b0e-4234-ae28-f997728054fa',
    'order_version': 2,
    'line_item_id': '822d77c4-00a6-4fb9-909b-094ef0b8c4b9',
    'item_quantity': 1,
    'from_state_id': '8f2e888e-9777-4557-9a7f-c649153770c2',
    'to_state_key': TwoUKeys.SUCCESS_FULFILMENT_STATE
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

EXAMPLE_COMMERCETOOLS_ORDER_RETURNED_MESSAGE = {
    "detail": {
        "id": "db116fbd-3f62-468e-810a-a68eb6e15bfe",
        "version": 1,
        "versionModifiedAt": "2024-04-15T13:13:06.104Z",
        "sequenceNumber": 2,
        "resource": {
            "typeId": "order",
            "id": "debb493b-5f1e-43ee-af22-8dff50d8acd3"
        },
        "resourceVersion": 2,
        "resourceUserProvidedIdentifiers": {
            "orderNumber": "cart-id-ebc80b80-65c0-416c-a532-54cdafd20796"
        },
        "type": "ReturnInfoAdded",
        "returnInfo": {
            "items": [
                {
                    "type": "LineItemReturnItem",
                    "id": "d26cd880-72a4-4467-b1c4-1efa65dd5156",
                    "quantity": 1,
                    "lineItemId": "5259bfe2-86cb-4cf6-87c7-550561d882b1",
                    "shipmentState": "Returned",
                    "paymentState": "Initial",
                    "lastModifiedAt": "2024-04-15T13:13:06.083Z",
                    "createdAt": "2024-04-15T13:13:06.083Z"
                }
            ],
            "returnTrackingId": "5259bfe2-86cb-4cf6-87c7-550561d882b1",
            "returnDate": "2024-04-15T00:00:00.000Z"
        },
        "createdAt": "2024-04-15T13:13:06.104Z",
        "lastModifiedAt": "2024-04-15T13:13:06.104Z",
        "lastModifiedBy": {
            "isPlatformClient": True,
            "user": {
                "typeId": "user",
                "id": "e0761f02-d7d5-4592-9332-a3bf6abc2539"
            }
        },
        "createdBy": {
            "isPlatformClient": True,
            "user": {
                "typeId": "user",
                "id": "e0761f02-d7d5-4592-9332-a3bf6abc2539"
            }
        }
    }
}

