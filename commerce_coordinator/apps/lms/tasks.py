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
        f'LMS fulfill_order_placed_send_enroll_in_course_task fired with user {edx_lms_user_id},'
        f'course_id {course_id}, mode {mode}, SKU {partner_sku}, '
        f'for titan_order_uuid {titan_order_uuid} placed on {date_placed},'
        f'with coupon {coupon_code}.'
    )
    # TODO: make the API call to LMS here.
    if edx_lms_username:
        logger.info('Calling LMS enrollment API...')
