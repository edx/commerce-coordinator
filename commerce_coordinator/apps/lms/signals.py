"""
LMS app signals and receivers.
"""
import logging

from commerce_coordinator.apps.core.signal_helpers import log_receiver
from commerce_coordinator.apps.lms.tasks import fulfill_order_placed_send_enroll_in_course_task
from commerce_coordinator.apps.core.signal_helpers import CoordinatorSignal

order_created_signal = CoordinatorSignal()

logger = logging.getLogger(__name__)

@log_receiver(logger)
def fulfill_order_placed_send_enroll_in_course(**kwargs):
    """
    Fulfill the order placed in Titan with a Celery task to LMS to enroll a user in a single course.
    """
    async_result = fulfill_order_placed_send_enroll_in_course_task.delay(
        course_id=kwargs['course_id'],
        course_mode=kwargs['course_mode'],
        date_placed=kwargs['date_placed'],
        edx_lms_user_id=kwargs['edx_lms_user_id'],
        email_opt_in=kwargs['email_opt_in'],
        order_number=kwargs['order_number'],
        provider_id=kwargs['provider_id'],
    )
    return async_result.id
