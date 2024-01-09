"""
LMS App Testing Data Constants
"""
from typing import Dict, Union

EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD: Dict[str, Union[str, bool, int, None]] = {
    'course_id': 'course-v1:edX+DemoX+Demo_Course',
    'course_mode': 'verified',
    'date_placed': '2023-04-17T13:30:33Z',
    'edx_lms_user_id': 4,
    'email_opt_in': False,
    'order_number': '61ec1afa-1b0e-4234-ae28-f997728054fa',
    'provider_id': None,
    'source_system': 'test',
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
            'name': 'order_placed',
            'value': '2023-04-17T13:30:33Z'
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
