"""
Titan Celery tasks
"""
from celery import shared_task
from celery.utils.log import get_task_logger

# Use the special Celery logger for our tasks
logger = get_task_logger(__name__)


@shared_task()
def enrollment_code_redemption_requested_create_order_task(user_id, sku, enrollment_code):
    """
    Enrollment code redemption.
    """
    logger.info('Titan enrollment_code_redemption_requested_create_order_task fired '
                f'with user {user_id} and sku {sku} and enrollment_code {enrollment_code}.')
