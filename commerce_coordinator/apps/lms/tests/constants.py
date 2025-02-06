"""
LMS App Testing Data Constants
"""

from datetime import datetime
from typing import Dict, Union

_INIT_DATE = datetime.now().strftime('%b %d, %Y')

EXAMPLE_LINE_ITEM_STATE_PAYLOAD = {
    'order_id': '61ec1afa-1b0e-4234-ae28-f997728054fa',
    'order_version': 2,
    'line_item_id': '822d77c4-00a6-4fb9-909b-094ef0b8c4b9',
    'item_quantity': 1,
    'line_item_state_id': '8f2e888e-9777-4557-9a7f-c649153770c2',
}

EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD: Dict[str, Union[str, bool, int, None]] = {
    'course_id': 'course-v1:edX+DemoX+Demo_Course',
    'course_mode': 'verified',
    'date_placed': _INIT_DATE,
    'edx_lms_user_id': 4,
    'email_opt_in': False,
    'order_number': '61ec1afa-1b0e-4234-ae28-f997728054fa',
    'order_id': '61ec1afa-1b0e-4234-ae28-f997728054fa',
    'order_version': 2,
    'provider_id': None,
    'source_system': 'test',
    'line_item_id': '822d77c4-00a6-4fb9-909b-094ef0b8c4b9',
    'item_quantity': 1,
    'line_item_state_id': '8f2e888e-9777-4557-9a7f-c649153770c2',
    'message_id': '1063f19c-08f3-41a4-a952-a8577374373c',
    'user_first_name': 'test',
    'user_email': 'test@example.com',
    'course_title': 'Demonstration Course',
    'product_type': 'Self Paced Course'
}

EXAMPLE_FULFILLMENT_REQUEST_PAYLOAD = {
    'user': 'test-user',
    'mode': 'verified',
    'is_active': True,
    'course_details': {
        'course_id': 'course-v1:edX+DemoX+Demo_Course'
    },
    'email_opt_in': False,
    'enrollment_attributes': [
        {
            'namespace': 'order',
            'name': 'order_number',
            'value': '61ec1afa-1b0e-4234-ae28-f997728054fa'
        },
        {
            'namespace': 'order',
            'name': 'order_id',
            'value': '61ec1afa-1b0e-4234-ae28-f997728054fa'
        },
        {
            'namespace': 'order',
            'name': 'line_item_id',
            'value': '822d77c4-00a6-4fb9-909b-094ef0b8c4b9',
        },
        {
            'namespace': 'order',
            'name': 'date_placed',
            'value': _INIT_DATE,
        },
        {
            'namespace': 'order',
            'name': 'source_system',
            'value': 'test'
        }
    ]
}

EXAMPLE_FULFILLMENT_RESPONSE_PAYLOAD = {
    'course_details': {
        'course_end': None,
        'course_id': 'course-v1:edX+DemoX+Demo_Course',
        'course_modes': [
            {
                'bulk_sku': None,
                'currency': 'usd',
                'description': None,
                'expiration_datetime': None,
                'min_price': 0,
                'name': 'Audit',
                'sku': '68EFFFF',
                'slug': 'audit',
                'suggested_prices': ''
            },
            {
                'bulk_sku': 'A5B6DBE',
                'currency': 'usd',
                'description': None,
                'expiration_datetime': '2024-03-13T14:12:05.024240Z',
                'min_price': 149,
                'name': 'Verified Certificate',
                'sku': '8CF08E5',
                'slug': 'verified',
                'suggested_prices': ''
            }
        ],
        'course_name': 'Demonstration Course',
        'course_start': '2013-02-05T05:00:00Z',
        'enrollment_end': None,
        'enrollment_start': '2013-02-05T00:00:00Z',
        'invite_only': False,
        'pacing_type': 'Instructor Paced'
    },
}

EXAMPLE_FULFILLMENT_LOGGING_OBJ = {
    'user': 'test-user',
    'lms_user_id': 4,
    'order_id': '61ec1afa-1b0e-4234-ae28-f997728054fa',
    'course_id': 'course-v1:edX+DemoX+Demo_Course',
    'message_id': '1063f19c-08f3-41a4-a952-a8577374373c',
    'celery_task_id': None
}
