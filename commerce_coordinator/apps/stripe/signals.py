"""
Stripe signals and receivers.
"""
from commerce_coordinator.apps.core.signal_helpers import CoordinatorSignal

payment_processed_signal = CoordinatorSignal()
payment_refunded_signal = CoordinatorSignal()
