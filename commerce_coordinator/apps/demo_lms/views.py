"""
Views for the Demo LMS app which implement the API endpoints or callback handlers.
"""

from django.http import JsonResponse

from commerce_coordinator.apps.core.signal_helpers import format_signal_results
from commerce_coordinator.apps.core.signals import test_signal

from .filters import SampleDataRequested
from .signals import purchase_complete_signal


def _format_signal_send_response(results):
    """
    Takes the return value from a signal send_robust and returns a JSON HTTP response
    """
    data = format_signal_results(results)
    return JsonResponse(data)


def test_view(_):
    """
    DEMO: Test view for the proof-of-concept. It exists simply to show that we can call signals mapped in settings
    and how we can potentially handle responses / exceptions from receivers.

    Returns a JSON object with the results of our signal call, including string formatting traceback on an exception.
    """
    # This should fail, we don't allow a non-robust send!
    # test_signal.send("Something")

    # send_robust() will ensure all receivers are called, as opposed to send() which will return immediately upon
    # any failure, causing some receivers to never be called.
    results = test_signal.send_robust("Something")

    return _format_signal_send_response(results)


def demo_purchase_complete(_):
    """
    Demonstrate a complex workflow that utilizes both fanout and serial steps.

    This call kicks off a stubbed out version of what might happen when we get a callback from a payment provider for
    a purchase of a bundle of courses. It fires a single signal, which has a listeners that represent several downstream
    services. Some of those services (order history) are only hit once per order, some (lms) get a call for each course
    in the bundle.
    """
    # Normally this data would come from a POST callback from a payment provider, but I'm putting it in this format
    # for simplicity of testing and to make the structure obvious.
    callback_results = {
        'order_id': 'EDX-12345',
        'user_id': 1313,
        'status': 'success',
        'cost': 1.00,
        'products': [
            'SKU123',
            'SKU456',
            'SKU789'
        ]
    }

    # Send the signal for anything that cares about an order (as defined in settings). This should be three receivers:
    # - Order history (kicks off a celery task to make an API call)
    # - Email service (confirmation email gets sent)
    # - LMS (enrolls the learner in all 3 courses by firing an enrollment signal for each course, which has a secondary
    #       handler that kicks off a Celery task which sends an LMS API call for each)

    results = purchase_complete_signal.send_robust('demo_purchase_complete', order_results=callback_results)

    return _format_signal_send_response(results)


def demo_get_sample_data(_):
    """
    Demonstrate a workflow that gets data from providers configured as pipeline steps.
    """

    sample_data = SampleDataRequested.run_filter()
    return JsonResponse({"sample_data": sample_data})
