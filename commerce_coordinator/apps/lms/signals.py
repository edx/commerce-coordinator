"""
LMS app signals and receivers.
"""
import logging

logger = logging.getLogger(__name__)


def test_receiver(sender, **kwargs):
    logger.info(f"LMS TEST_RECEIVER CALLED with sender '{sender}'!")
