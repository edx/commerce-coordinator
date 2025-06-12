"""
Tests for IOSValidator - Validates iOS In-App Purchases using the App Store API.
"""

from unittest import TestCase, mock

from django.core.exceptions import ImproperlyConfigured
from inapppy import InAppPyValidationError
from testfixtures import LogCapture

from commerce_coordinator.apps.iap.ios_validator import IOSValidator

VALID_PURCHASE_TOKEN = "test.purchase.token"
INVALID_PURCHASE_TOKEN = "test.purchase.invalid_token"
SAMPLE_VALID_RESPONSE = {'message': 'valid_response'}
MOCK_PAYMENT_PROCESSOR_CONFIG = {
    'edx': {
        'ios_iap': {
            'ios_bundle_id': 'test.ios.bundle.id'
        }
    }
}


class AppStoreValidatorProxy:
    """Proxy for inapppy.AppStoreValidator"""

    def validate(self, purchase_token, exclude_old_transactions=False):  # pylint: disable=unused-argument
        if purchase_token == INVALID_PURCHASE_TOKEN:
            raise InAppPyValidationError("Invalid purchase token.")
        return SAMPLE_VALID_RESPONSE


class IOSValidatorTests(TestCase):
    """IOS Validator Tests"""

    def setUp(self):
        self.validator = IOSValidator()

    @mock.patch('commerce_coordinator.apps.iap.ios_validator.settings')
    @mock.patch('commerce_coordinator.apps.iap.ios_validator.AppStoreValidator')
    def test_validate_successful(self, mock_appstore_validator, mock_settings):
        mock_settings.PAYMENT_PROCESSOR_CONFIG = MOCK_PAYMENT_PROCESSOR_CONFIG
        mock_appstore_validator.return_value = AppStoreValidatorProxy()

        response = self.validator.validate(VALID_PURCHASE_TOKEN)
        self.assertEqual(response, SAMPLE_VALID_RESPONSE)

    @mock.patch('commerce_coordinator.apps.iap.ios_validator.settings')
    @mock.patch('commerce_coordinator.apps.iap.ios_validator.AppStoreValidator')
    def test_validate_failed(self, mock_appstore_validator, mock_settings):
        mock_settings.PAYMENT_PROCESSOR_CONFIG = MOCK_PAYMENT_PROCESSOR_CONFIG
        mock_appstore_validator.return_value = AppStoreValidatorProxy()
        logger_name = 'commerce_coordinator.apps.iap.ios_validator'

        with LogCapture(logger_name) as ios_validator_log_capture:
            response = self.validator.validate(INVALID_PURCHASE_TOKEN)
            ios_validator_log_capture.check_present(
                (
                    logger_name,
                    'ERROR',
                    'Purchase validation failed None',
                ),
            )
            self.assertIn('error', response)

    @mock.patch('commerce_coordinator.apps.iap.ios_validator.settings')
    def test_missing_configuration(self, mock_settings):
        mock_settings.PAYMENT_PROCESSOR_CONFIG = {'edx': {'ios_iap': {}}}

        with self.assertRaises(ImproperlyConfigured) as context:
            self.validator.validate(VALID_PURCHASE_TOKEN)

        self.assertIn("Invalid iOS configuration.", str(context.exception))
