'''Test the utilities that help test Coordinator apps.'''
# Quis custodiet ipsos custodes?

from unittest.mock import MagicMock, patch

from commerce_coordinator.apps.core.tests.utils import CoordinatorClientTestCase


class CoordinatorClientTestCaseTests(CoordinatorClientTestCase):
    '''
    Tests for CoordinatorClientTestCase.
    '''

    @patch('commerce_coordinator.apps.core.tests.utils.responses')
    def test_json_expected_request(self, mock_responses):
        '''Check test passes when responses.calls[-1].request.body matches expected_request.'''
        mock_responses.calls[0].request.body = '{"dummy_param": "dummy_val"}'
        self.assertJSONClientResponse(
            uut=MagicMock(),
            input_kwargs={},
            request_type='json',
            expected_request={'dummy_param': 'dummy_val'},
            mock_method='POST',
            mock_url='example.com',
        )

    @patch('commerce_coordinator.apps.core.tests.utils.responses')
    def test_invalid_request_type(self, mock_responses):
        '''Check for raise when given bad request_type'''
        mock_responses.calls[0].request.body = '{"dummy_param": "dummy_val"}'
        with self.assertRaises(ValueError):
            self.assertJSONClientResponse(
                uut=MagicMock(),
                input_kwargs={},
                request_type='bad_request_type',  # This is the test.
                expected_request={'dummy_param': 'dummy_val'},
                mock_method='POST',
                mock_url='example.com',
            )

    def test_expected_output(self):
        '''Check test is successful when output matches expected_output. '''
        self.assertJSONClientResponse(
            uut=MagicMock(return_value='normal_output'),
            input_kwargs={},
            mock_url='example.com',
            expected_output='normal_output',
        )

    def test_expected_output_empty_on_exception(self):
        '''Check for raise when uut throws exception when expecting output.'''
        with self.assertRaises(AssertionError):
            self.assertJSONClientResponse(
                uut=MagicMock(side_effect=Exception('Unexpected')),
                input_kwargs={},
                mock_url='example.com',
                expected_output='normal_output',  # This is the test.
            )
