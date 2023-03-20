"""
LMS Celery tasks
"""
from celery import shared_task
from celery.utils.log import get_task_logger

from commerce_coordinator.apps.core.models import User
from commerce_coordinator.apps.lms.clients import LMSAPIClient

# Use the special Celery logger for our tasks
logger = get_task_logger(__name__)


@shared_task()
def fulfill_order_placed_send_enroll_in_course_task(
    course_id,
    course_mode,
    date_placed,
    edx_lms_user_id,
    email_opt_in,
    order_number,
    provider_id,
):
    """
    Celery task for order placed fulfillment and enrollment via LMS Enrollment API.
    """
    logger.info(
        f'LMS fulfill_order_placed_send_enroll_in_course_task fired with {locals()},'
    )

    user = User.objects.get(lms_user_id=edx_lms_user_id)

    enrollment_data = {
        'user': user.username,
        'mode': course_mode,
        'is_active': True,
        'course_details': {
            'course_id': course_id
        },
        'email_opt_in': email_opt_in,
        'enrollment_attributes': [
            {
                'namespace': 'order',
                'name': 'order_number',
                'value': order_number,
            },
            {
                'namespace': 'order',
                'name': 'order_placed',
                'value': date_placed,
            }
        ]
    }

    if course_mode == 'credit':
        enrollment_data['enrollment_attributes'].append({
            'namespace': 'credit',
            'name': 'provider_id',
            'value': provider_id,
        })

    return LMSAPIClient().enroll_user_in_course(enrollment_data)
