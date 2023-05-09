'''Utilities to help test Coordinator apps.'''

import json
import random
import string

import responses
from django.apps import apps
from django.conf import settings
from django.test import TestCase

from commerce_coordinator.apps.core.clients import urljoin_directory
from commerce_coordinator.apps.core.signal_helpers import CoordinatorSignal

example_signal = CoordinatorSignal()

ANGRY_FACE = '\U0001F92C'


class CoordinatorSignalReceiverTestCase(TestCase):
    '''
    Test a CoordinatorSignal receiver.

    Example:
        Use by subclassing like this::

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
        Checks that uut produces expected_request and expected_output given input_kwargs and mock_response.

        Mocks any calls by requests to self.mock_url. Returns mock_response for those calls as JSON.

        Optionally, checks headers match self.expected_headers.

        Args:
            uut (callable): Unit under test. Calls an external API using the `requests` library.
            input_kwargs (dict): kwargs to provide uut.
            expected_request (dict): Expected request of uut to external API given input_kwargs. POST requests will be
                converted to JSON.
            expected_headers (dict): Expected headers of uut to external API.
            mock_url (str): URL of external API to mock.
            mock_response (dict): Mock response external API should provide uut given expected_request. Will be
                converted to JSON.
            mock_status (int): HTTP Status Code
            mock_method (str): String of the Mocked Method (GET, POST, etc)
            expected_output (object): Expected return value of uut given mock_response.

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


def name_test(name: str, test_packed_params):
    """
    Permits the naming of simple ddt packed tests in common collection containers

    NOTE: This may "feel weird" but it's the way the developers do it see
    `def annotated(str, list)` at https://ddt.readthedocs.io/en/latest/example.html
    """

    class WrappedTuple(tuple):
        pass

    class WrappedList(list):
        pass

    class WrappedDict(dict):
        pass

    wrapped_test_params = None
    if isinstance(test_packed_params, dict):
        wrapped_test_params = WrappedDict(test_packed_params)
    elif isinstance(test_packed_params, tuple):
        wrapped_test_params = WrappedTuple(test_packed_params)
    elif isinstance(test_packed_params, list):  # coverage skipping here is a bug. sorry.
        wrapped_test_params = WrappedList(test_packed_params)

    # See note in Class PyDoc, Parameterized PyTest is planned in the future.
    # pylint: disable-next=literal-used-as-attribute
    setattr(wrapped_test_params, "__name__", name)
    return wrapped_test_params


def random_unicode_str(ln: int, limit_unicode=True, weight_divisor=2):
    """ Generate a string of X characters guaranteed to include at least one non ASCII one. """

    uchars = ['\xe9', '\xf1', '\xfc', '\u0110', '\u0159', '\u016f', '\xc5', '\xdf', '\xe7', '\u0131',
              '\u0130', '\uff21', '\ufb04', '\u211a', '\xbd', '\u20ac', '\u20b9', '\xa5', '\u0416', '\u03b7',
              '\uae00', '\u0913', '\u0b15', '\u3058', '\u5b57', '\U0001f40d', '\U0001f496', '\u2652', '\u2658']

    # The above represents, Escapes used incase this file is ever re-encoded by accident.
    # ['é', 'ñ', 'ü', 'Đ', 'ř', 'ů', 'Å', 'ß', 'ç', 'ı', 'İ', 'Ａ', 'ﬄ', 'ℚ', '½', '€', '₹', '¥', 'Ж', 'η', '글',
    # 'ओ', 'କ', 'じ', '字', '🐍', '💖', '♒', '♘']

    chars = uchars + list(string.printable)

    def _unicode_limiter(c: (int, str)):
        """ Map replacement function to limit unicode based on a divisor """

        if limit_unicode:
            if len(bytes(chars[c[0]], encoding='utf8')) > 1:
                return 1
            else:
                return abs(len(chars) / weight_divisor)
        else:
            return 1

    weights = list(map(_unicode_limiter, enumerate(chars)))

    retval = ''.join(random.choices(chars, weights=weights, k=ln - 1))

    retval += random.choice(uchars)  # ensure we get one unicode no matter what.

    assert len(retval) == ln
    return retval
