"""
LMS app signals and receivers.
"""

from commerce_coordinator.apps.core.signal_helpers import CoordinatorSignal

order_created_signal = CoordinatorSignal()

fulfillment_completed_update_ct_line_item_signal = CoordinatorSignal()
