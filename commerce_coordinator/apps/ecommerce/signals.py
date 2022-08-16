"""
Ecommerce signals and receivers.
"""
import logging

from commerce_coordinator.apps.core.signal_helpers import CoordinatorSignal

logger = logging.getLogger(__name__)

enrollment_code_redemption_requested_signal = CoordinatorSignal()
