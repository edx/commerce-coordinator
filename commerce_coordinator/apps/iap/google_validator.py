"""
Google Play Validator Module for In-App Purchase (IAP) Validation.

This module provides functionality for validating Google Play in-app purchases
using the inapppy library.
"""

import logging

from django.conf import ImproperlyConfigured, settings
from inapppy import GooglePlayVerifier, errors

logger = logging.getLogger(__name__)


class GooglePlayValidator:
    """
    A validator for Google Play In-App Purchases using Google Play's API.

    Methods:
        validate(receipt, course_run_key):
            Validates a Google Play purchase receipt.
    """

    def validate(self, receipt: dict, course_run_key: str) -> dict:
        """
        Validates the purchase token with Google Play.

        Args:
            receipt (dict): The receipt dictionary containing the purchase token.
            course_run_key (str): The product SKU (now course_run_key) for the purchase.

        Returns:
            dict: Validation response with raw response and status flags.
        """
        bundle_id = getattr(settings, 'GOOGLE_BUNDLE_ID', None)
        google_service_account_key_file = getattr(settings, 'GOOGLE_SERVICE_ACCOUNT_KEY_FILE', None)

        if not bundle_id or not google_service_account_key_file:
            logger.error("Google Play configuration missing 'GOOGLE_BUNDLE_ID' or 'GOOGLE_SERVICE_ACCOUNT_KEY_FILE'.")
            raise ImproperlyConfigured("Invalid Google Play configuration.")

        try:
            verifier = GooglePlayVerifier(bundle_id, google_service_account_key_file)
            response = verifier.verify_with_result(
                receipt.get('purchase_token'),
                course_run_key,
                is_subscription=False
            )

            return {
                'raw_response': response.raw_response,
                'is_canceled': response.is_canceled,
                'is_expired': response.is_expired
            }
        except errors.GoogleError as exc:
            logger.error('Google Play validation failed: %s', exc)
            return {
                'error': str(exc),
                'message': exc.message if hasattr(exc, 'message') else 'Unknown error occurred'
            }
