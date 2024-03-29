"""
Demo LMS app signals and receivers.
"""
import logging

from commerce_coordinator.apps.core.signal_helpers import CoordinatorSignal, log_receiver
from commerce_coordinator.apps.demo_lms.tasks import (
    demo_order_complete_send_confirmation_email_task,
    demo_order_complete_send_enroll_in_course_task,
    demo_order_complete_send_order_history_task
)

logger = logging.getLogger(__name__)

#############################################################
# DEMO: Proof-of-concept test code from here to end of file
#############################################################


@log_receiver(logger)
def test_receiver(**kwargs):
    """
    Basic signal receiver to test out connecting signals and handlers via config.
    Due to the log_receiver decorator, this is an example of what we'll emit to the logs:
    INFO 2394 [commerce_coordinator.apps.demo_lms.signals] test_receiver CALLED with sender '{sender}' and {kwargs}.
    """
    # This test can be modified accordingly to include more uses.


# The rest of this file is related to the "Purchase Complete" demo
purchase_complete_signal = CoordinatorSignal()
enroll_learner_signal = CoordinatorSignal()


@log_receiver(logger)
def demo_purchase_complete_order_history(**kwargs):
    """
    This signal receiver would typically be in a separate app for just the Order History service, but is here for
    convenience. It kicks off a Celery task that would normally make an API to a 3rd party order history service.
    """
    demo_order_complete_send_order_history_task.delay(kwargs['order_results'])


@log_receiver(logger)
def demo_purchase_complete_send_confirmation_email(**kwargs):
    """
    This signal receiver would typically be in a separate app for just the email service, but is here for
    convenience. It kicks off a Celery task that would normally make an API to a 3rd party email service to send
    an order confirmation.
    """
    demo_order_complete_send_confirmation_email_task.delay(kwargs['order_results'])


@log_receiver(logger)
def demo_purchase_complete_enroll_in_course(**kwargs):
    """
    This signal receiver is one that legitimately belongs in LMS, it first off an enrollment event for each purchased
    course in an order. Any number of signal handlers could care about that, but in this demo only
    demo_enroll_learner_in_course is hooked up.
    """
    user_id = kwargs['order_results']['user_id']
    for product_id in kwargs['order_results']['products']:
        enroll_learner_signal.send_robust('demo_purchase_complete', user_id=user_id, product_id=product_id)


@log_receiver(logger)
def demo_enroll_learner_in_course(**kwargs):
    """
    This signal receiver is one that legitimately belongs in LMS, it would kick off a Celery task to LMS to enroll a
    user in a single course.
    """
    user_id = kwargs['user_id']
    product_id = kwargs['product_id']
    demo_order_complete_send_enroll_in_course_task.delay(user_id, product_id)
