"""
Commerce Coordinator helper methods for ensuring consistency with Django signal handling.
"""

from django.dispatch import Signal


class CoordinatorSignal(Signal):
    def send(self, *args, **kwargs):
        raise NotImplementedError("Coordinator Signals do not implement the send method. Use send_robust instead.")
