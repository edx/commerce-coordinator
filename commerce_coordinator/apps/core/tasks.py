"""
Core Celery tasks
"""
from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.cache import cache

TASK_LOCK_EXPIRE = 60 * 1  # Lock expires in 1 minute
TASK_LOCK_RETRY = 3  # Retry acquiring lock after 3 sceonds


# Use the special Celery logger for our tasks
logger = get_task_logger(__name__)


@shared_task()
def debug_task():  # pragma no cover
    logger.info('Core debug_task fired.')


def acquire_task_lock(task_id):
    """
    Mark the specified task_id as being in progress.

    This is used to make sure that the same task is not worked on by more than one worker
    at the same time.  This can occur when tasks are requeued by Celery in response to
    loss of connection to the task broker.  Most of the time, such duplicate tasks are
    run sequentially, but they can overlap in processing as well.

    Returns true if the task_id was not already locked; false if it was.
    """
    # cache.add fails if the key already exists
    key = f"task-{task_id}"
    succeeded = cache.add(key, 'true', TASK_LOCK_EXPIRE)
    if not succeeded:
        logger.info("task_id '%s': already locked.", task_id)
    return succeeded


def release_task_lock(task_id):
    """
    Unmark the specified task_id as being no longer in progress.

    This is most important to permit a task to be retried.
    """
    # According to Celery task cookbook, "Memcache delete is very slow, but we have
    # to use it to take advantage of using add() for atomic locking."
    key = f"task-{task_id}"
    cache.delete(key)
