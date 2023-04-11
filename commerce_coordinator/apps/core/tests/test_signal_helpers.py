"""Test core.signal_helpers."""

import logging
from pprint import pformat

from django.apps import apps
from django.test import TestCase, override_settings

from commerce_coordinator.apps.core.signal_helpers import CoordinatorSignal, format_signal_results, log_receiver

# Log using module name.
logger = logging.getLogger(__name__)

# Fully qualified module name.
fqmn = __name__

# Test signal & receivers.
mock_signal = CoordinatorSignal()


@log_receiver(logger)
def mock_receiver_1(**kwargs):
    """No-op receiver that returns a bogus task id"""
    return 'bogus_mock_receiver_1_task_id'


@log_receiver(logger)
def mock_receiver_2(**kwargs):
    """No-op receiver that logs parameters and returns a bogus task id"""
    param1 = kwargs['param1']
    param2 = kwargs['param2']
    logger.info(f'mock_receiver called with {param1}, {param2}')
    return 'bogus_mock_receiver_2_task_id'


@log_receiver(logger)
def mock_receiver_exception(**kwargs):
    """No-op receiver that raises an exception"""
    raise RuntimeError('This is an expected exception.')


@log_receiver(logger)
def mock_receiver_innocent_bystander(**kwargs):
    """No-op receiver that should never be called"""
    raise RuntimeError('This receiver should never be set up or called.')


class CoordinatorSignalTestCase(TestCase):
    """Base class for testing CoordinatorSignal."""

    def setUp(self):
        # Initialize store for signal result.
        self.result = None

        # Initialize context manager for holding test logs.
        self.logging_cm = None

        # Clear receiver connections from previous tests.
        mock_signal.receivers = []
        mock_signal.sender_receivers_cache.clear()

        # Remount signals after settings override.
        apps.get_app_config('core').ready()

        # Send mock_signal.
        parameters = {
            'param1': 'parameter1_value',
            'param2': 'parameter2_value',
        }

        with self.assertLogs() as self.logging_cm:
            self.result = mock_signal.send_robust(
                sender=self.__class__,
                **parameters
            )


@override_settings(
    CC_SIGNALS={
        fqmn + '.mock_signal': [
            fqmn + '.mock_receiver_1',
        ],
    }
)
class CoordinatorSignalTests(CoordinatorSignalTestCase):
    """Tests of CoordinatorSignal class."""

    def test_config_matches_num_calls(self):
        logger.info('self.result: %s', self.result)
        self.assertEqual(len(self.result), 1,
                         'Check 1 receiver is called')

    def test_return_has_name_and_result(self):
        logger.info('self.result: %s', self.result)
        self.assertEqual(len(self.result[0]), 2,
                         'Check receiver self.result has name and self.result')

    def test_correct_receiver_called(self):
        logger.info('self.result: %s', self.result)
        self.assertEqual(self.result[0][0].__name__, 'mock_receiver_1',
                         'Check receiver name is mock_receiver')

    def test_correct_response_returned(self):
        logger.info('self.result: %s', self.result)
        self.assertEqual(self.result[0][1], 'bogus_mock_receiver_1_task_id',
                         'Check reciever self.result is a task id')

    def test_correct_arguments_passed(self):
        logger.info('self.logging_cm.output: %s', self.logging_cm.output)
        self.assertTrue(any('parameter1_value' in line for line in self.logging_cm.output),
                        'Check parameter1_value is received by receiver')
        self.assertTrue(any('parameter2_value' in line for line in self.logging_cm.output),
                        'Check parameter2_value is received by receiver')

    def test_exception_on_unrobust_send(self):
        with self.assertRaises(NotImplementedError):
            self.result = mock_signal.send(
                sender=self.__class__
            )


@override_settings(
    CC_SIGNALS={
        fqmn + '.mock_signal': [
            fqmn + '.mock_receiver_1',
            fqmn + '.mock_receiver_2',
            fqmn + '.mock_receiver_exception',
        ],
    }
)
class LogReceiverTests(CoordinatorSignalTestCase):
    """Tests of log_receiver() helper function."""

    def test_config_matches_num_calls(self):
        logger.info('self.result: %s', self.result)
        self.assertEqual(len(self.result), 3,
                         'Check 3 receivers called')

    def test_mock_receiver_exception_called(self):
        logger.info('self.result: %s', self.result)
        self.assertTrue(
            any(
                receiver.__name__ == 'mock_receiver_exception'
                for receiver, response in self.result
            ),
            'Check mock_receiver_exception called'
        )

    def test_mock_receiver_exception_reported(self):
        logger.info('self.result: %s', self.result)
        self.assertTrue(
            any(
                receiver.__name__ == 'mock_receiver_exception'
                and isinstance(response, RuntimeError)
                for receiver, response in self.result
            ),
            'Check mock_receiver_exception reports its RuntimeError'
        )

    def test_mock_receiver_exception_logged(self):
        logger.info('self.logging_cm.output: %s', self.logging_cm.output)
        self.assertTrue(
            any(
                'This is an expected exception' in line
                for line in self.logging_cm.output
            ),
            'Check mock_receiver_exception\'s RuntimeError is logged'
        )


@override_settings(
    CC_SIGNALS={
        fqmn + '.mock_signal': [
            fqmn + '.mock_receiver_1',
            fqmn + '.mock_receiver_2',
            fqmn + '.mock_receiver_exception',
        ],
    }
)
class FormatSignalResultsTests(CoordinatorSignalTestCase):
    """Tests of format_signal_results() helper function."""

    def setUp(self):
        super().setUp()

        # Format results
        self.formatted_result = format_signal_results(self.result)

    def test_returns_dict(self):
        logger.info('self.formatted_result: \n%s', pformat(self.formatted_result))
        logger.info('type(self.formatted_result): %s', type(self.formatted_result))
        self.assertIsInstance(self.formatted_result, dict,
                              'Check output is a Python dict')

    def test_config_matches_num_formatted_result_entries(self):
        logger.info('self.formatted_result: \n%s', pformat(self.formatted_result))
        self.assertEqual(len(self.formatted_result), 3,
                         'Check 3 results are returned, one for each signal')

    def test_formatted_result_shape(self):
        logger.info('self.result: %s', self.result)
        logger.info('self.formatted_result: \n%s', pformat(self.formatted_result))

        for value in self.formatted_result.values():
            self.assertIsInstance(value, dict,
                                  'Check each output value is a dict')
            self.assertIn('error', value.keys(),
                          'Check dict for each output value has key called error')
            self.assertIn('response', value.keys(),
                          'Check dict for each output value has key called response')

    def test_mock_receiver_1_result(self):
        logger.info('self.result: %s', self.result)
        logger.info('self.formatted_result: \n%s', pformat(self.formatted_result))

        self.assertIn('mock_receiver_1', self.formatted_result,
                      'Check results have entry for mock_receiver_1')

        entry = self.formatted_result['mock_receiver_1']

        self.assertFalse(entry['error'],
                         'Check mock_receiver_1 reports no error')

        self.assertEqual(entry['response'], 'bogus_mock_receiver_1_task_id',
                         'Check mock_receiver_1 reports its return value')

    def test_mock_receiver_exception_result(self):
        logger.info('self.result: %s', self.result)
        logger.info('self.formatted_result: \n%s', pformat(self.formatted_result))

        self.assertIn('mock_receiver_exception', self.formatted_result,
                      'Check results have entry for mock_receiver_exception')

        entry = self.formatted_result['mock_receiver_exception']

        self.assertTrue(entry['error'],
                        'Check mock_receiver_exception reports an error')

        self.assertTrue(any('RuntimeError' in line for line in entry['response']),
                        'Check mock_receiver_exception contains RuntimeError info')