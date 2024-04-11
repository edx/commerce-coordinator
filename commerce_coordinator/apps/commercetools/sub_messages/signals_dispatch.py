"""
Commcercetools Subscription Message Signals
"""
from commerce_coordinator.apps.core.signal_helpers import CoordinatorSignal

fulfill_order_placed_message_signal = CoordinatorSignal()
fulfill_order_sanctioned_message_signal = CoordinatorSignal()
fulfill_order_returned_signal = CoordinatorSignal()
