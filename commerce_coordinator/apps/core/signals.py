"""
Core app signals and receivers.
"""
import logging

from .signal_helpers import CoordinatorSignal
from .tasks import debug_celery_signal_task, debug_task

logger = logging.getLogger(__name__)


#############################################################
# FIXME: Proof-of-concept test code from here to end of file
#############################################################
test_signal = CoordinatorSignal()
test_celery_signal = CoordinatorSignal()


def test_receiver_exception(sender, **kwargs):
    """
    Output some debug information and throw an error.

    This test receiver is part of the proof-of-concept. It exists to provide an example in the upstream code of
    how an exception could be handled.
    """
    logger.info(f"CORE TEST_RECEIVER_EXCEPTION CALLED with sender '{sender}'!")
    raise Exception("Oh no, something went wrong!")


def test_celery_task(sender, **kwargs):
    logger.info(f"Queuing Celery task debug_task from sender '{sender}'.")

    # This takes places our call to the Celery task on the redis queue. The actual debug_task function will be called
    # inside the Celery process when it finds the new message on the queue.
    debug_task.delay()


def test_celery_signal_task(sender, **kwargs):
    logger.info(f"Queuing Celery task debug_celery_signal_task from sender '{sender}'.")
    debug_celery_signal_task.delay()