"""
LMS Celery tasks
"""
import json

from datetime import datetime

from celery import Task, shared_task
from celery.utils.log import get_task_logger
from django.contrib.auth import get_user_model
from requests import RequestException

from commerce_coordinator.apps.commercetools.catalog_info.constants import TwoUKeys
from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient
from commerce_coordinator.apps.commercetools.utils import send_fulfillment_error_email
from commerce_coordinator.apps.lms.clients import LMSAPIClient

# Use the special Celery logger for our tasks
logger = get_task_logger(__name__)
User = get_user_model()


class CourseEnrollTaskAfterReturn(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        error_message = json.loads(exc.response.text).get('message', '')
        edx_lms_user_id = kwargs.get('edx_lms_user_id')
        user_email = kwargs.get('user_email')
        order_number = kwargs.get('order_number')
        user_first_name = kwargs.get('user_first_name')
        course_title = kwargs.get('course_title')

        logger.error(
            f"Task {self.name} failed after max retries with error message: {error_message} "
            f"for user with User Id: {edx_lms_user_id}, Email: {user_email}, "
            f"Order Number: {order_number}, Course Title: {course_title}"
        )

        if (
            self.request.retries >= self.max_retries
            and "course mode is expired or otherwise unavailable for course run" in error_message
        ):

            logger.info(
                f"Sending Fulfillment Error Email for user with "
                f"User ID: {edx_lms_user_id}, Email: {user_email}, "
                f"Order Number: {order_number}, Course Title: {course_title}"
            )

            canvas_entry_properties = {
                'order_number': order_number,
                'product_type': 'course',
                'product_name': course_title,
                'first_name': user_first_name,
            }
            # Send failure notification email
            send_fulfillment_error_email(edx_lms_user_id, user_email, canvas_entry_properties)


@shared_task(
    bind=True,
    autoretry_for=(RequestException,),
    retry_kwargs={'max_retries': 5, 'countdown': 3},
    base=CourseEnrollTaskAfterReturn,
)
def fulfill_order_placed_send_enroll_in_course_task(
    self,
    course_id,
    course_mode,
    date_placed,
    edx_lms_user_id,
    email_opt_in,
    order_number,
    order_id,
    order_version,
    provider_id,
    source_system,
    line_item_id,
    item_quantity,
    line_item_state_id,
    message_id,
    user_first_name,
    user_email,
    course_title
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
                'name': 'order_id',
                'value': order_id,
            },
            {
                'namespace': 'order',
                'name': 'line_item_id',
                'value': line_item_id,
            },
            {
                'namespace': 'order',
                'name': 'date_placed',
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
    if self.request.retries > 0:
        client = CommercetoolsAPIClient()
        # A retry means the current line item state on the order would be a failure state
        line_item_state_id = client.get_state_by_key(TwoUKeys.FAILURE_FULFILMENT_STATE).id
        start_time = datetime.now()
        order_version = client.get_order_by_id(order_id).version
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"[Performance Check] get_order_by_id call took {duration} seconds")

    line_item_state_payload = {
        'order_id': order_id,
        'order_version': order_version,
        'line_item_id': line_item_id,
        'item_quantity': item_quantity,
        'line_item_state_id': line_item_state_id,
    }

    fulfillment_logging_obj = {
        'user': user.username,
        'lms_user_id': user.lms_user_id,
        'order_id': order_id,
        'course_id': course_id,
        'message_id': message_id,
        'celery_task_id': self.request.id
    }

    return LMSAPIClient().enroll_user_in_course(enrollment_data, line_item_state_payload, fulfillment_logging_obj)
