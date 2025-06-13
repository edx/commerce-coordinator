"""
iOS Validator Module for In-App Purchase (IAP) Validation.

This module provides functionality for validating iOS in-app purchases
using the App Store validation API through the inapppy library.
"""

import logging

from django.conf import ImproperlyConfigured, settings
from inapppy import AppStoreValidator, InAppPyValidationError

logger = logging.getLogger(__name__)


class IOSValidator:
    """
    A validator for iOS In-App Purchases using Apple's App Store validation API.

    Methods:
        validate(receipt):
            Validates an iOS receipt with Apple's App Store API.
    """

    def validate(self, purchase_token):
        """
        Validates the provided iOS purchase receipt.

        Args:
            purchase_token (str): The purchase token received from the client.

        Returns:
            dict: The validation result from the App Store, or an error message if validation fails.
        """
        configuration = settings.PAYMENT_PROCESSOR_CONFIG["edx"]["ios_iap"]
        bundle_id = configuration.get("ios_bundle_id")

        if not bundle_id:
            logger.error("iOS configuration missing 'IOS_BUNDLE_ID'.")
            raise ImproperlyConfigured("Invalid iOS configuration.")

        validator = AppStoreValidator(bundle_id, auto_retry_wrong_env_request=True)

        try:
            validation_result = validator.validate(
                purchase_token,
                exclude_old_transactions=True
            )
        except InAppPyValidationError as ex:
            logger.error('Purchase validation failed %s', ex.raw_response)
            return {'error': ex.raw_response}

        logger.info("iOS IAP validated successfully.")
        return validation_result
