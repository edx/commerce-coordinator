'''Utilities to help test Coordinator apps.'''

import json

import responses
from django.apps import apps
from django.test import TestCase

from commerce_coordinator.apps.core.signal_helpers import CoordinatorSignal

example_signal = CoordinatorSignal()


class CoordinatorSignalReceiverTestCase(TestCase):
    '''
    Test a CoordinatorSignal receiver.

    Use by subclassing like this:

        from django.test import override_settings

        from commerce_coordinator.apps.core.tests.utils import CoordinatorSignalReceiverTestCase

        @override_settings(
            CC_SIGNALS={
                'commerce_coordinator.apps.core.tests.utils.example_signal': [
                    'commerce_coordinator.apps.your_app.signals.receiver_under_test',
                ],
            }
        )
        class ReceiverUnderTestTests(CoordinatorSignalReceiverTestCase):

            mock_parameters =  {
                'param1': 'parameter1_value',
                'param2': 'parameter2_value',
            }

            def test_config_matches_num_calls(self):
                self.assertEqual(len(self.result), 1, 'Check 1 receiver is called')

        ...

    '''

    # Signal to fire.
    mock_signal = example_signal

    # Parameters to send with fired signal.
    mock_parameters = {
        'parameter_name': 'parameter_value',
    }

    def setUp(self):
        # Initialize store for signal result.
        self.result = None

        # Initialize context manager for holding test logs.
        self.logging_cm = None

        # Clear receiver connections from previous tests.
        self.mock_signal.receivers = []
        self.mock_signal.sender_receivers_cache.clear()

        # Remount signals after settings override.
        apps.get_app_config('core').ready()

        # Send mock_signal.
        with self.assertLogs() as self.logging_cm:
            self.result = self.mock_signal.send_robust(
                sender=self.__class__,
                **self.mock_parameters
            )


class CoordinatorClientTestCase(TestCase):
    '''
    Testing class for methods of clients.py of a Coordinator app.

    Note: There is no class named CoordinatorClient. This is a utility class.
    '''

    mock_method = 'POST'
    expected_headers = None

    @responses.activate
    def assertJSONClientResponse(self, uut, input_kwargs, expected_request,
                                 mock_url, mock_response, expected_output):
        '''
        Checks uut produces expected_request and expected_output given
        input_kwargs and mock_response.

        Mocks any calls by requests to self.mock_url. Returns
        mock_response for those calls as JSON.

        Checks headers match self.expected_headers.

        Args:
            uut (callable): Unit under test. Calls an external API using the
                requests library.
            input_kwargs (dict): kwargs to provide uut.
            expected_request (dict): Expected request of uut to external API
                given input_kwargs. Will be converted to JSON.
            mock_url (str): URL of external API to mock.
            mock_response (dict): Mock response external API should provide uut
                given expected_request. Will be converted to JSON.
            expected_output (object): Expected return value of uut given
                mock_response.
        '''
        # Prepare external API's mock response:
        responses.add(
            method=self.mock_method,
            url=mock_url,
            json=mock_response,
        )

        # Get client output & request it built for external API:
        output = uut(**input_kwargs)
        request = responses.calls[-1].request

        # Perform checks:
        self.assertGreaterEqual(
            request.headers.items(),
            self.expected_headers.items(),
            'Check external API called with expected headers'
        )
        self.assertEqual(
            json.loads(request.body),
            expected_request,
            'Check external API called with expected input'
        )
        self.assertEqual(
            output,
            expected_output,
            'Check client returns expected output'
        )
