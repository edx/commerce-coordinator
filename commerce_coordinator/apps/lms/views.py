"""
Views for the LMS app
"""

import traceback

from django.http import JsonResponse

from commerce_coordinator.apps.core.signals import test_signal


def test_view(_):
    """
    FIXME: Test view for the proof-of-concept. It exists simply to show that we can call signals mapped in settings
    and how we can potentially handle responses / exceptions from receivers.

    Returns a JSON object with the results of our signal call, including string formatting traceback on an exception.
    """
    # This should fail, we don't allow a non-robust send!
    # test_signal.send("Something")

    # send_robust() will ensure all receivers are called, as opposed to send() which will return immediately upon
    # any failure, causing some receivers to never be called.
    results = test_signal.send_robust("Something")

    # The results of a send_robust are a tuple of a reference to the method called and the exception, if one was raised
    data = {}
    for receiver, response in results:
        receiver_name = str(receiver)

        if response and response.__traceback__:
            traceback_list = traceback.format_tb(response.__traceback__)
            response_str = str(response) + " " + "\n".join(traceback_list)
        elif response:
            response_str = str(response)
        else:
            response_str = ""

        result_dict = {receiver_name: response_str}
        data.update(result_dict)

    return JsonResponse(data)
