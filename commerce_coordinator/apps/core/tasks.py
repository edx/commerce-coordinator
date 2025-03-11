"""
Core Celery tasks
"""
from celery import shared_task
from celery.utils.log import get_task_logger

# Use the special Celery logger for our tasks
logger = get_task_logger(__name__)


@shared_task()
def debug_task():  # pragma no cover
    logger.info('Core debug_task fired.')
