"""
Ecommerce signals and receivers.
"""
from commerce_coordinator.apps.core.signal_helpers import CoordinatorSignal

enrollment_code_redemption_requested_signal = CoordinatorSignal()
fulfill_order_placed_signal = CoordinatorSignal()
order_created_signal = CoordinatorSignal()
