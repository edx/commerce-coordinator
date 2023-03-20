"""
LMS app signals and receivers.
"""
import logging

from commerce_coordinator.apps.core.signal_helpers import log_receiver
from commerce_coordinator.apps.lms.tasks import fulfill_order_placed_send_enroll_in_course_task

logger = logging.getLogger(__name__)


@log_receiver(logger)
def fulfill_order_placed_send_enroll_in_course(**kwargs):
    """
    Fulfill the order placed in Titan with a Celery task to LMS to enroll a user in a single course.
    """
    fulfill_order_placed_send_enroll_in_course_task.delay(
        coupon_code=kwargs['coupon_code'],
        course_id=kwargs['course_id'],
        date_placed=kwargs['date_placed'],
        edx_lms_user_id=kwargs['edx_lms_user_id'],
        edx_lms_username=kwargs['edx_lms_username'],
        mode=kwargs['mode'],
        partner_sku=kwargs['partner_sku'],
        titan_order_uuid=kwargs['titan_order_uuid'],
    )
