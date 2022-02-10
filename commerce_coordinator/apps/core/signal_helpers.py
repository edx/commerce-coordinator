"""
Commerce Coordinator helper methods for ensuring consistency with Django signal handling.
"""
import functools
import inspect

from django.dispatch import Signal


class CoordinatorSignal(Signal):
    def send(self, *args, **kwargs):
        raise NotImplementedError("Coordinator Signals do not implement the send method. Use send_robust instead.")


def coordinator_receiver(logger):
    """
    Return a decorated function with LMS log messages.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            """
            Wrapper function around the original function or method.
            """
            try:
                sender = kwargs['sender']
                logger.info(f"LMS {func.__name__} CALLED with sender '{sender}' and {kwargs}")
                return func(*args, **kwargs)
            except Exception as e:
                logger.exception(f"Something went wrong! Exception raised in {func.__name__} with error {repr(e)}")
                raise e
        return wrapper
    return decorator
