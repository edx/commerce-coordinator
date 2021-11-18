"""
LMS Celery tasks
"""
from celery import shared_task
from celery.utils.log import get_task_logger

# Use the special Celery logger for our tasks
logger = get_task_logger(__name__)


@shared_task()
def demo_order_complete_send_order_history_task(order_info):
    """
    Stub Celery task for a fake order history integration.

    Normally this is where we would make an API call to the 3rd party API.
    """
    logger.info(f'LMS demo_order_complete_send_order_history_task fired with order info {order_info}.')


@shared_task()
def demo_order_complete_send_confirmation_email_task(order_info):
    """
    Stub Celery task for a fake email service integration.

    Normally this is where we would make an API call to the 3rd party API.
    """
    logger.info(f'LMS demo_order_complete_send_confirmation_email_task fired order info {order_info}.')


@shared_task()
def demo_order_complete_send_enroll_in_course_task(user_id, course_id):
    """
    Stub Celery task for a fake LMS course enrollment integration.

    Normally this is where we would make an API call to LMS.
    """
    logger.info(f'LMS demo_order_complete_send_enroll_in_course_task fired with user {user_id} and course {course_id}.')
