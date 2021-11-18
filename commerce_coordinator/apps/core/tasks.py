"""
Core Celery tasks
"""
from celery import shared_task
from celery.utils.log import get_task_logger


# Use the special Celery logger for our tasks
logger = get_task_logger(__name__)


@shared_task()
def debug_task():
    logger.info('Core debug_task fired.')


@shared_task()
def debug_celery_signal_task():
    # Note: Using signals from tasks is likely to create a circular import since the normal paradigm is to call tasks
    # from signals! Working around that here.
    from .signals import test_signal

    logger.info('Core debug_celery_signal_task fired.')

    # As long as the Celery worker is using almost identical configuration to the Django server you can use the same
    # signals and handlers from inside a Celery task. This is a simple one that just fires off the test signal, which
    # in turn will queue another Celery task for "debug_task" that should also execute.
    test_signal.send_robust("Sending a signal from a celery task!")

