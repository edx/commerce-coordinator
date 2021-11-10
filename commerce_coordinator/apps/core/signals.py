"""
Core app signals and receivers.
"""
import logging

from commerce_coordinator.apps.core.signal_helpers import CoordinatorSignal

logger = logging.getLogger(__name__)


#############################################################
# FIXME: Proof-of-concept test code from here to end of file
#############################################################
test_signal = CoordinatorSignal()


def test_receiver_exception(sender, **kwargs):
    """
    Output some debug information and throw an error.

    This test receiver is part of the proof-of-concept. It exists to provide an example in the upstream code of
    how an exception could be handled.
    """
    logger.info(f"CORE TEST_RECEIVER_EXCEPTION CALLED with sender '{sender}'!")
    raise Exception("Oh no, something went wrong!")
