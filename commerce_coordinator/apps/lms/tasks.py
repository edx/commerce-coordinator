"""
LMS Celery tasks
"""

from celery import shared_task
from celery.utils.log import get_task_logger
from requests import RequestException

from commerce_coordinator.apps.commercetools.catalog_info.constants import TwoUKeys
from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient
from commerce_coordinator.apps.core.models import User
from commerce_coordinator.apps.lms.clients import LMSAPIClient

# Use the special Celery logger for our tasks
logger = get_task_logger(__name__)


@shared_task(bind=True, autoretry_for=(RequestException,), retry_kwargs={'max_retries': 5, 'countdown': 3})
def fulfill_order_placed_send_enroll_in_course_task(
    self,
    course_id,
    course_mode,
    date_placed,
    edx_lms_user_id,
    email_opt_in,
    order_number,
    order_version,
    provider_id,
    source_system,
    line_item_id,
    item_quantity,
    line_item_state_id,
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

    # Updating the order version and stateID after the transition to 'Fulfillment Failure'
    if self.request.retries > 0:  # pragma no cover
        client = CommercetoolsAPIClient()
        # A retry means the current line item state on the order would be a failure state
        line_item_state_id = client.get_state_by_key(TwoUKeys.FAILURE_FULFILMENT_STATE).id
        order_version = client.get_order_by_id(order_number).version

    line_item_state_payload = {
        'order_id': order_number,
        'order_version': order_version,
        'line_item_id': line_item_id,
        'item_quantity': item_quantity,
        'line_item_state_id': line_item_state_id,
    }

    return LMSAPIClient().enroll_user_in_course(enrollment_data, line_item_state_payload)
