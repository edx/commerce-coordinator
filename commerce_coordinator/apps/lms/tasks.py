"""
LMS Celery tasks
"""
from celery import shared_task
from celery.utils.log import get_task_logger

# Use the special Celery logger for our tasks
logger = get_task_logger(__name__)


@shared_task()
def fulfill_order_placed_send_enroll_in_course_task(
    coupon_code,
    course_id,
    date_placed,
    edx_lms_user_id,
    mode,
    partner_sku,
    titan_order_uuid,
    edx_lms_username,
):
    """
    Celery task for order placed fulfillment and enrollment via LMS Enrollment API.
    """
    logger.info(
        f'LMS fulfill_order_placed_send_enroll_in_course_task fired with coupon {coupon_code},'
        f'course ID {course_id}, on {date_placed}, for LMS user ID {edx_lms_user_id}, with mode {mode},'
        f'SKU {partner_sku}, for Titan Order: {titan_order_uuid}.'
    )

    # TODO: make the API call to LMS here.
    # Temporary if statement below since username is PII and cannot
    # be logged but will be used as enrollment data in the next commit
    if edx_lms_username:
        logger.info('Calling LMS enrollment API...')
