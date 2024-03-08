"""
LMS Celery tasks
"""

from celery import shared_task
from celery.utils.log import get_task_logger
from requests import RequestException

from commerce_coordinator.apps.core.models import User
from commerce_coordinator.apps.lms.clients import LMSAPIClient
from commerce_coordinator.apps.lms.signals import fulfillment_completed_signal

# Use the special Celery logger for our tasks
logger = get_task_logger(__name__)


@shared_task(autoretry_for=(RequestException,), retry_kwargs={'max_retries': 5, 'countdown': 3})
def fulfill_order_placed_send_enroll_in_course_task(
    course_id,
    course_mode,
    date_placed,
    edx_lms_user_id,
    email_opt_in,
    order_number,
    order_version,
    provider_id,
    source_system,
    item_id,
    item_quantity,
    state_ids,
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
            },
            {
                'namespace': 'order',
                'name': 'source_system',
                'value': source_system,
            },
        ]
    }

    if course_mode == 'credit':
        enrollment_data['enrollment_attributes'].append({
            'namespace': 'credit',
            'name': 'provider_id',
            'value': provider_id,
        })

    return_val = LMSAPIClient().enroll_user_in_course(enrollment_data)
    logger.info(f'-- RETURN_VAL {return_val}--')
    fulfill_line_item_state_payload = {
        'order_id': order_number,
        'order_version': order_version,
        'item_id': item_id,
        'item_quantity': item_quantity,
        'state_ids': state_ids,
        # 'response_status': return_val.status_code
    }
    logger.info('-- SENDING SIG POST FULFILL --')
    fulfillment_completed_signal.send_robust(
        sender=None,
        **fulfill_line_item_state_payload
    )

    return return_val
