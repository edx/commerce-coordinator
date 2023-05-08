'''Utilities to help test Coordinator apps.'''

import json

import responses
from django.apps import apps
from django.conf import settings
from django.test import TestCase

from commerce_coordinator.apps.core.clients import urljoin_directory
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

    def fire_signal(self):
        '''Send mock_signal.'''
        with self.assertLogs() as logs:
            result = self.mock_signal.send_robust(
                sender=self.__class__,
                **self.mock_parameters
            )
        return (result, logs)


class CoordinatorClientTestCase(TestCase):
    '''
    Testing class for methods of clients.py of a Coordinator app.

    Note: There is no class named CoordinatorClient. This is a utility class.

    '''

    @responses.activate
    def assertJSONClientResponse(
        self,
        *,
        uut,
        input_kwargs,
        expected_request=None,
        expected_headers=None,
        mock_method='POST',
        mock_url,
        mock_response=None,
        mock_status=200,
        expected_output=None
    ):
        '''
        Checks uut produces expected_request and expected_output given
        input_kwargs and mock_response.

        Mocks any calls by requests to self.mock_url. Returns
        mock_response for those calls as JSON.

        Optionally, checks headers match self.expected_headers.

        Args:
            uut (callable): Required. Unit under test. Calls an external API
                using the requests library.
            input_kwargs (dict): Required. kwargs to provide uut.
            expected_request (dict): Expected request of uut to external API
                given input_kwargs. POST requests will be converted to JSON.
            expected_headers (dict): Expected headers of uut to external API.
            mock_method (str): Method of mocked request. Defaults to POST.
            mock_url (str): Required. URL of external API to mock.
            mock_response (dict): Mock response external API should provide uut
                given expected_request. Will be converted to JSON.
            mock_status (int): Mock response status code external API should
                provide uut given expected_request.
            expected_output (object): Expected return value of uut given
                mock_response.
        '''
        is_get = mock_method == 'GET'

        # Use matcher for query params for GET requests:
        if is_get:
            expected_match = [
                responses.matchers.query_param_matcher(expected_request)
            ]
        else:
            expected_match = []

        # Prepare external API's mock response:
        if not mock_response:
            mock_response = {}
        responses.add(
            method=mock_method,
            url=mock_url,
            status=mock_status,
            json=mock_response,
            match=expected_match,
        )

        # Get client output & request it built for external API.
        # Throw exceptions after asserts.
        exception_thrown = None
        try:
            output = uut(**input_kwargs)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            # Will rethrow this exception later.
            exception_thrown = exc

        request = responses.calls[-1].request

        # Perform checks:
        if expected_headers:
            self.assertGreaterEqual(
                request.headers.items(),
                expected_headers.items(),
                'Check external API called with expected headers'
            )
        if expected_request:
            if is_get:
                request_dict = request.params
            else:
                request_dict = json.loads(request.body)
            self.assertEqual(
                request_dict,
                expected_request,
                'Check external API called with expected input'
            )
        if expected_output:
            if exception_thrown:
                self.fail('Cannot validate expected_output on exceptions.')
            self.assertEqual(
                output,
                expected_output,
                'Check client returns expected output'
            )

        # Re-throw exception after checks:
        if exception_thrown:
            raise exception_thrown


class CoordinatorOAuthClientTestCase(CoordinatorClientTestCase):
    '''
    Testing class for methods of OAuth clients.py of a Coordinator app.

    Note: There is no class named CoordinatorOAuthClient. This is a utility class.

    '''

    def register_mock_oauth_call(self):
        '''
        Add a mock OAuth call to
        settings.BACKEND_SERVICE_EDX_OAUTH2_PROVIDER_URL's
        /oauth/access_token endpoint.
        '''
        url = urljoin_directory(
            settings.BACKEND_SERVICE_EDX_OAUTH2_PROVIDER_URL,
            '/oauth2/access_token'
        )
        responses.add(method='POST', url=url, json={
            'access_token': 'a1b2c3d4',
            'expires_in': 1000
        })

    @responses.activate
    def assertJSONClientResponse(
        self,
        *,
        uut,
        input_kwargs,
        expected_request=None,
        expected_headers=None,
        mock_method='POST',
        mock_url,
        mock_response=None,
        mock_status=200,
        expected_output=None
    ):
        self.register_mock_oauth_call()
        super().assertJSONClientResponse(
            uut=uut,
            input_kwargs=input_kwargs,
            expected_request=expected_request,
            expected_headers=expected_headers,
            mock_method=mock_method,
            mock_url=mock_url,
            mock_response=mock_response,
            mock_status=mock_status,
            expected_output=expected_output
        )
