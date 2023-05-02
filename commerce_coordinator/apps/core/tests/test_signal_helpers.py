"""Test core.signal_helpers."""

import logging
from pprint import pformat

from django.test import override_settings

from commerce_coordinator.apps.core.signal_helpers import format_signal_results, log_receiver
from commerce_coordinator.apps.core.tests.utils import CoordinatorSignalReceiverTestCase

# Log using module name.
logger = logging.getLogger(__name__)

# Test signal & receivers.
test_signal_helpers_parameters = {
    'param1': 'parameter1_value',
    'param2': 'parameter2_value',
}


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


@override_settings(
    CC_SIGNALS={
        'commerce_coordinator.apps.core.tests.utils.example_signal': [
            'commerce_coordinator.apps.core.tests.test_signal_helpers.mock_receiver_1',
        ],
    }
)
class CoordinatorSignalTests(CoordinatorSignalReceiverTestCase):
    """Tests of CoordinatorSignal class."""

    mock_parameters = test_signal_helpers_parameters

    def test_config_matches_num_calls(self):
        result, _ = self.fire_signal()
        logger.info('result: %s', result)
        self.assertEqual(len(result), 1,
                         'Check 1 receiver is called')

    def test_return_has_name_and_result(self):
        result, _ = self.fire_signal()
        logger.info('result: %s', result)
        self.assertEqual(len(result[0]), 2,
                         'Check receiver result has name and result')

    def test_correct_receiver_called(self):
        result, _ = self.fire_signal()
        logger.info('result: %s', result)
        self.assertEqual(result[0][0].__name__, 'mock_receiver_1',
                         'Check receiver name is mock_receiver')

    def test_correct_response_returned(self):
        result, _ = self.fire_signal()
        logger.info('result: %s', result)
        self.assertEqual(result[0][1], 'bogus_mock_receiver_1_task_id',
                         'Check reciever result is a task id')

    def test_correct_arguments_passed(self):
        _, logs = self.fire_signal()
        logger.info('logs.output: %s', logs.output)
        self.assertTrue(any('parameter1_value' in line for line in logs.output),
                        'Check parameter1_value is received by receiver')
        self.assertTrue(any('parameter2_value' in line for line in logs.output),
                        'Check parameter2_value is received by receiver')

    def test_exception_on_unrobust_send(self):
        self.fire_signal()
        with self.assertRaises(NotImplementedError):
            self.mock_signal.send(
                sender=self.__class__
            )


@override_settings(
    CC_SIGNALS={
        'commerce_coordinator.apps.core.tests.utils.example_signal': [
            'commerce_coordinator.apps.core.tests.test_signal_helpers.mock_receiver_1',
            'commerce_coordinator.apps.core.tests.test_signal_helpers.mock_receiver_2',
            'commerce_coordinator.apps.core.tests.test_signal_helpers.mock_receiver_exception',
        ],
    }
)
class LogReceiverTests(CoordinatorSignalReceiverTestCase):
    """Tests of log_receiver() helper function."""

    mock_parameters = test_signal_helpers_parameters

    def test_config_matches_num_calls(self):
        result, _ = self.fire_signal()
        logger.info('result: %s', result)
        self.assertEqual(len(result), 3,
                         'Check 3 receivers called')

    def test_mock_receiver_exception_called(self):
        result, _ = self.fire_signal()
        logger.info('result: %s', result)
        self.assertTrue(
            any(
                receiver.__name__ == 'mock_receiver_exception'
                for receiver, response in result
            ),
            'Check mock_receiver_exception called'
        )

    def test_mock_receiver_exception_reported(self):
        result, _ = self.fire_signal()
        logger.info('result: %s', result)
        self.assertTrue(
            any(
                receiver.__name__ == 'mock_receiver_exception'
                and isinstance(response, RuntimeError)
                for receiver, response in result
            ),
            'Check mock_receiver_exception reports its RuntimeError'
        )

    def test_mock_receiver_exception_logged(self):
        _, logs = self.fire_signal()
        logger.info('logs.output: %s', logs.output)
        self.assertTrue(
            any(
                'This is an expected exception' in line
                for line in logs.output
            ),
            'Check mock_receiver_exception\'s RuntimeError is logged'
        )


@override_settings(
    CC_SIGNALS={
        'commerce_coordinator.apps.core.tests.utils.example_signal': [
            'commerce_coordinator.apps.core.tests.test_signal_helpers.mock_receiver_1',
            'commerce_coordinator.apps.core.tests.test_signal_helpers.mock_receiver_2',
            'commerce_coordinator.apps.core.tests.test_signal_helpers.mock_receiver_exception',
        ],
    }
)
class FormatSignalResultsTests(CoordinatorSignalReceiverTestCase):
    """Tests of format_signal_results() helper function."""

    mock_parameters = test_signal_helpers_parameters

    def test_returns_dict(self):
        result, _ = self.fire_signal()
        formatted_result = format_signal_results(result)
        logger.info('formatted_result: \n%s', pformat(formatted_result))
        logger.info('type(formatted_result): %s', type(formatted_result))
        self.assertIsInstance(formatted_result, dict,
                              'Check output is a Python dict')

    def test_config_matches_num_formatted_result_entries(self):
        result, _ = self.fire_signal()
        formatted_result = format_signal_results(result)
        logger.info('formatted_result: \n%s', pformat(formatted_result))
        self.assertEqual(len(formatted_result), 3,
                         'Check 3 results are returned, one for each signal')

    def test_formatted_result_shape(self):
        result, _ = self.fire_signal()
        formatted_result = format_signal_results(result)
        logger.info('result: %s', result)
        logger.info('formatted_result: \n%s', pformat(formatted_result))

        for value in formatted_result.values():
            self.assertIsInstance(value, dict,
                                  'Check each output value is a dict')
            self.assertIn('error', value.keys(),
                          'Check dict for each output value has key called error')
            self.assertIn('response', value.keys(),
                          'Check dict for each output value has key called response')

    def test_mock_receiver_1_result(self):
        result, _ = self.fire_signal()
        formatted_result = format_signal_results(result)
        logger.info('result: %s', result)
        logger.info('formatted_result: \n%s', pformat(formatted_result))

        self.assertIn('mock_receiver_1', formatted_result,
                      'Check results have entry for mock_receiver_1')

        entry = formatted_result['mock_receiver_1']

        self.assertFalse(entry['error'],
                         'Check mock_receiver_1 reports no error')

        self.assertEqual(entry['response'], 'bogus_mock_receiver_1_task_id',
                         'Check mock_receiver_1 reports its return value')

    def test_mock_receiver_exception_result(self):
        result, _ = self.fire_signal()
        formatted_result = format_signal_results(result)
        logger.info('result: %s', result)
        logger.info('formatted_result: \n%s', pformat(formatted_result))

        self.assertIn('mock_receiver_exception', formatted_result,
                      'Check results have entry for mock_receiver_exception')

        entry = formatted_result['mock_receiver_exception']

        self.assertTrue(entry['error'],
                        'Check mock_receiver_exception reports an error')

        self.assertTrue(any('RuntimeError' in line for line in entry['response']),
                        'Check mock_receiver_exception contains RuntimeError info')
