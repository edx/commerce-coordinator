"""
LMS Celery tasks
"""

import json
from datetime import datetime

from celery import Task, shared_task
from celery.utils.log import get_task_logger
from commercetools import CommercetoolsError
from django.contrib.auth import get_user_model
from requests import RequestException

from commerce_coordinator.apps.commercetools.catalog_info.constants import TwoUKeys
from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient
from commerce_coordinator.apps.commercetools.constants import CT_ORDER_PRODUCT_TYPE_FOR_BRAZE
from commerce_coordinator.apps.commercetools.utils import send_unsupported_mode_fulfillment_error_email
from commerce_coordinator.apps.lms.clients import LMSAPIClient

# Use the special Celery logger for our tasks
logger = get_task_logger(__name__)
User = get_user_model()


class CourseEnrollTaskAfterReturn(Task):    # pylint: disable=abstract-method
    """
    Base class for fulfill_order_placed_send_enroll_in_course_task
    """

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        edx_lms_user_id = kwargs.get('edx_lms_user_id')
        user_email = kwargs.get('user_email')
        order_number = kwargs.get('order_number')
        user_first_name = kwargs.get('user_first_name')
        course_title = kwargs.get('course_title')
        product_type = kwargs.get('product_type')

        error_message = (
            json.loads(exc.response.text).get('message', '')
            if isinstance(exc, RequestException) and exc.response is not None and getattr(exc.response, "text", '')
            else str(exc)
        )

        logger.error(
            f"Post-purchase fulfillment task {self.name} failed after max "
            f"retries with the error message: {error_message} "
            f"for user with user Id: {edx_lms_user_id}, email: {user_email}, "
            f"order number: {order_number}, and course title: {course_title}"
        )

        # These errors can be either returned from LMS enrollment API or can be due to connection timeouts.
        fulfillment_error_messages = [
            "course mode is expired or otherwise unavailable for course run",
            "Read timed out.",
            "Service Unavailable"
        ]

        if any(err_msg in error_message for err_msg in fulfillment_error_messages):
            logger.info(
                f"Sending unsupported course mode fulfillment error email "
                f"for the user with user ID: {edx_lms_user_id}, email: {user_email}, "
                f"order number: {order_number}, and course title: {course_title}"
            )

            braze_product_type = CT_ORDER_PRODUCT_TYPE_FOR_BRAZE.get(product_type, 'course')

            canvas_entry_properties = {
                'order_number': order_number,
                'product_type': braze_product_type,
                'product_name': course_title,
                'first_name': user_first_name,
            }
            # Send failure notification email
            send_unsupported_mode_fulfillment_error_email(edx_lms_user_id, user_email, canvas_entry_properties)


@shared_task(
    bind=True,
    autoretry_for=(RequestException, CommercetoolsError),
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
    user_first_name,    # pylint: disable=unused-argument
    user_email,         # pylint: disable=unused-argument
    course_title,        # pylint: disable=unused-argument
    product_type        # pylint: disable=unused-argument
):
    """
    Celery task for order placed fulfillment and enrollment via LMS Enrollment API.
    """
    tag = "fulfill_order_placed_send_enroll_in_course_task"
    logger.info(f"{tag} Starting task with details: {locals()}.")
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
        logger.warning(f"{tag} "
                       f"Task retry count# {self.request.retries} for CT order ID {order_id}.")
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
