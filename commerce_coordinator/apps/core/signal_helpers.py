"""
Commerce Coordinator helper methods for ensuring consistency with Django signal handling.
"""
import functools
import traceback

from django.dispatch import Signal


class CoordinatorSignal(Signal):
    def send(self, *args, **kwargs):
        raise NotImplementedError("Coordinator Signals do not implement the send method. Use send_robust instead.")


def coordinator_receiver(logger):
    """
    Return a decorated function with log messages.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            """
            Wrapper function around the original function or method.
            """
            try:
                # Django's signal dispatcher will give the sender as a keyword argument
                sender = kwargs['sender']
                logger.info(f"{func.__name__} CALLED with sender '{sender}' and {kwargs}")
                return func(*args, **kwargs)
            except Exception as e:
                logger.exception(f"Something went wrong! Exception raised in {func.__name__} with error {repr(e)}")
                raise e
        return wrapper
    return decorator

def format_signal_results(results):
    """
    Takes the return value from a signal send_robust and returns a dict with formatted results.
    """
    # The results of a send_robust are a tuple of a reference to the method called and the exception, if one was raised
    data = {}
    for receiver, response in results:
        receiver_name = str(receiver)
        exception_occurred = bool(response and response.__traceback__)
        if exception_occurred:
            response_str = traceback.format_exception(
                type(response),
                response,
                response.__traceback__,
            )
        elif response:
            response_str = str(response)
        else:
            response_str = ""

        result_dict = { receiver_name: { "response": response_str, "error": exception_occurred } }
        data.update(result_dict)
    return data
