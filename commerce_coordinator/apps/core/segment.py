"""
Convenience functions for working with the segment.io analytics library
"""

import logging

from django.conf import settings
from segment import analytics

logger = logging.getLogger(__name__)


def track(
    lms_user_id=None,
    event=None,
    properties=None,
    context=None,
    timestamp=None,
    anonymous_id=None,
    integrations=None,
    message_id=None
):
    """
    Wrapper around segment.io's track function that checks for the presence of
    the SEGMENT_KEY setting before sending the event to segment.io
    """
    if settings.SEGMENT_KEY:
        analytics.track(lms_user_id, event, properties, context, timestamp, anonymous_id, integrations, message_id)
    else:
        logger.debug(f"{event} for user {lms_user_id} not tracked because SEGMENT_KEY is not set.")
        logger.info(f"EVENT PROPSSS {event} {properties}")
