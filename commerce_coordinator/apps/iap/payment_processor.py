"""
IAP Payment Processor Module.

This module provides the IAPPaymentProcessor class for handling In-App Purchase (IAP)
validation for Android (Google Play) and iOS (App Store) platforms.
"""

import logging

from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient
from commerce_coordinator.apps.iap.google_validator import GooglePlayValidator
from commerce_coordinator.apps.iap.ios_validator import IOSValidator

logger = logging.getLogger(__name__)


class IAPPaymentProcessor:
    """
    A payment processor for In-App Purchases (IAP) using platform-specific validators.

    Attributes:
        client (CommercetoolsAPIClient): The commercetools API client instance.
    """

    def __init__(self):
        self.client = CommercetoolsAPIClient()

    def validate_iap(self, request_data, cart) -> dict:
        """
        Validates IAP (In-App Purchase) based on the 'payment_processor' value in request_data.

        Args:
            request_data (dict): A dictionary containing IAP data, including
                                 'purchase_token', 'course_run_key', and 'payment_processor'.

        Returns:
            dict: The validation result or an error message.
        """
        purchase_token = request_data.get('purchase_token')
        course_run_key = request_data.get('course_run_key')
        payment_processor = request_data.get('payment_processor')

        if not payment_processor:
            error_msg = "Missing 'payment_processor' in request data."
            logger.error(error_msg)
            return {'error': error_msg}

        # Select validator based on payment_processor value
        if payment_processor == 'android-iap':
            validator = GooglePlayValidator()
            validation_response = validator.validate(purchase_token, course_run_key)
        elif payment_processor == 'ios-iap':
            validator = IOSValidator()
            validation_response = validator.validate(purchase_token)
        else:
            error_msg = f"Unsupported payment_processor: {payment_processor}"
            logger.error(error_msg)
            return {'error': error_msg}

        if 'error' in validation_response:
            logger.error("Validation failed for %s: %s", payment_processor, validation_response['error'])
            return validation_response

        # Now handle platform-specific post-validation logic
        if payment_processor == 'android-iap':
            return self._handle_android_validation(validation_response, cart)
        else:  # ios-iap
            return self._handle_ios_validation(validation_response, course_run_key, cart)

    def _handle_android_validation(self, validation_response: dict, cart) -> dict:
        """
        Handle Android-specific IAP validation logic.

        Args:
            validation_response (dict): The validation response from Google Play.

        Returns:
            dict: The processed validation result.
        """
        transaction_id = validation_response.get('raw_response', {}).get('orderId')
        if not transaction_id:
            error_message = "Android IAP validation missing transaction ID."
            logger.error(error_message)
            return {'error': error_message}

        if validation_response.get('is_canceled'):
            error_message = f'Android payment is cancelled for [{transaction_id}]'
            logger.error(error_message)
            return {'error': error_message}

        if validation_response.get('is_expired'):
            error_message = f"Android payment is expired for [{transaction_id}]"
            logger.error(error_message)
            return {'error': error_message}

        is_redundant_payment = self.client.get_payment_by_transaction_id(transaction_id)
        if is_redundant_payment:
            error_message = f"Execute payment failed for basket [{cart}]. Redundant payment."
            logger.error(error_message)
            raise RedundantPaymentError(error_message)

        logger.info("Android IAP validated successfully.")
        return {
            'transaction_id': transaction_id,
            'validation_response': validation_response
        }

    def _handle_ios_validation(self, validation_response: dict, product_sku: str, cart) -> dict:
        """
        Handle iOS-specific IAP validation logic.

        Args:
            validation_response (dict): The validation response from App Store.
            product_sku (str): The SKU of the product to validate.

        Returns:
            dict: The processed validation result.
        """
        receipt = validation_response.get('receipt', {})
        in_app_purchases = receipt.get('in_app', [])

        # Find the specific purchase for the product SKU
        matched_purchase = next(
            (purchase for purchase in in_app_purchases if purchase.get('product_id') == product_sku),
            None
        )

        if not matched_purchase:
            logger.error("No matching iOS IAP purchase found for SKU: %s", product_sku)
            return {'error': 'No matching purchase found'}

        # Update the receipt to only include the matched purchase
        receipt['in_app'] = [matched_purchase]
        validation_response['receipt'] = receipt

        original_transaction_id = matched_purchase.get('original_transaction_id')

        # Check for cancellation
        if 'cancellation_reason' in matched_purchase:
            error_message = f'iOS payment is cancelled for [{original_transaction_id}] in basket [{cart}]'
            logger.error(error_message)
            return {'error': error_message}

        is_redundant_payment = self.client.get_payment_by_transaction_id(original_transaction_id)
        if is_redundant_payment:
            error_message = f"Execute payment failed for basket [{cart}]. Redundant payment."
            logger.error(error_message)
            raise RedundantPaymentError(error_message)

        logger.info("iOS IAP validated successfully.")
        return {
            'transaction_id': original_transaction_id,
            'validation_response': validation_response
        }


class RedundantPaymentError(Exception):
    """Exception raised for redundant payments detected."""
