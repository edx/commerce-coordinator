'''Constants for titan tests'''

from datetime import datetime
from uuid import UUID

import pytz

from commerce_coordinator.apps.titan.views import OrderFulfillView

EXAMPLE_FULFILLMENT_REQUEST_PAYLOAD = {
    'course_id': 'course-v1:edX+DemoX+Demo_Course',
    'course_mode': 'verified',
    'order_placed': 1681738233,
    'edx_lms_user_id': 4,
    'email_opt_in': 0,
    'order_number': '61ec1afa-1b0e-4234-ae28-f997728054fa',
    'source_system': 'titan',
}

EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD = {
    'sender': OrderFulfillView,
    'course_id': 'course-v1:edX+DemoX+Demo_Course',
    'course_mode': 'verified',
    'date_placed': datetime.fromtimestamp(1681738233, tz=pytz.utc),
    'edx_lms_user_id': 4,
    'email_opt_in': False,
    'order_number': UUID('61ec1afa-1b0e-4234-ae28-f997728054fa'),
    'provider_id': None,
    'source_system': 'titan',
}
