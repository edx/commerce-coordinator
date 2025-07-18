"""
IAP Payment Processor Module.

This module provides the IAPPaymentProcessor class for handling In-App Purchase (IAP)
validation for Android (Google Play) and iOS (App Store) platforms.
"""

import logging
from datetime import datetime, timezone

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from commerce_coordinator.apps.commercetools.catalog_info.constants import ANDROID_IAP, IOS_IAP
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

    RETRY_ATTEMPTS = 1
    AVAILABLE_ATTEMPTS = 2

    def __init__(self):
        self.client = CommercetoolsAPIClient()

    def parse_ios_receipt_date(self, date_str: str) -> datetime:
        """
        Parses an iOS-style receipt date string like '2025-06-12 10:58:27 Etc/GMT'
        and returns a UTC-aware datetime object.
        """
        date_str = date_str.replace(" Etc/GMT", "")
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)

    def _check_existing_payment(self, transaction_id: str, cart_id: str):
        """
        Checks if a payment with the given transaction ID exists and handles dangling or redundant cases.

        Returns:
            payment (object or None): The existing payment object or None if it doesn't exist.
        Raises:
            RedundantPaymentError: If payment exists and is not dangling.
        """
        payment = self.client.get_payment_by_transaction_interaction_id(transaction_id)
        if payment:
            if not self.client.is_dangling_payment(payment):
                msg = (
                    f"Redundant payment: existing payment found with transaction ID: {transaction_id}, "
                    f"already attached to a cart."
                )
                logger.error(msg)
                raise RedundantPaymentError(msg)

            logger.info(
                f"Dangling payment {payment.id} found with transaction ID: {transaction_id}. "
                f"Will reuse this payment for cart {cart_id}."
            )
        else:
            logger.info("No existing payment found. Proceeding to create new one.")
        return payment

    def get_consumable_ios_sku(self, price: int) -> str:
        """
        Returns the iOS consumable product ID (SKU) based on the given price.

        Args:
            price (int): Price of the product in USD.

        Returns:
            str: Corresponding product SKU string.
        """
        return f"mobile.ios.usd{int(price)}"

    def validate_iap(self, request_data, cart_id, price) -> dict:
        """
        Validates IAP (In-App Purchase) based on the 'payment_processor' value in request_data.
        """
        purchase_token = request_data.get('purchase_token')
        payment_processor = request_data.get('payment_processor')

        if payment_processor == ANDROID_IAP:
            validator = GooglePlayValidator()

            def validation_func():
                return self._validate_android(validator, purchase_token, price)

        elif payment_processor == IOS_IAP:
            validator = IOSValidator()

            def validation_func():
                return self._validate_ios(validator, purchase_token)

        else:
            error_msg = f"Unsupported payment_processor: {payment_processor}"
            logger.error(error_msg)
            raise ValidationError(error_msg)

        try:
            validation_response = self._retry_validation(validation_func, payment_processor)
        except Exception as e:
            logger.error("Exhausted all attempts to validate [%s] IAP. Final error: %s", payment_processor, str(e))
            raise ValidationError(str(e)) from e

        if payment_processor == ANDROID_IAP:
            return self._handle_android_validation(validation_response, cart_id)
        else:
            return self._handle_ios_validation(validation_response, price, cart_id)

    @retry(
        stop=stop_after_attempt(AVAILABLE_ATTEMPTS + RETRY_ATTEMPTS),
        wait=wait_fixed(1),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    def _retry_validation(self, validation_func, processor):
        """
        Executes the validation function with retries in case of exceptions.

        Args:
            validation_func (Callable): The validation function to retry.
            processor (str): The payment processor name, used for logging.

        Returns:
            dict: The successful validation response.

        Raises:
            Exception: If all retry attempts fail.
        """
        try:
            response = validation_func()
            if 'error' in response:
                raise Exception(response['error'])
            return response
        except Exception as e:
            logger.warning("Validation attempt failed for [%s]: %s", processor, str(e))
            raise

    def _validate_android(self, validator, purchase_token, price):
        return validator.validate(purchase_token, price)

    def _validate_ios(self, validator, purchase_token):
        return validator.validate(purchase_token)

    def _handle_android_validation(self, validation_response: dict, cart_id) -> dict:
        """
        Handle Android-specific IAP validation logic.

        Args:
            validation_response (dict): The validation response from Google Play.
            cart_id (str): The cart ID associated with the validation request.

        Returns:
            dict: The processed validation result.
        """
        transaction_id = validation_response.get('raw_response', {}).get('orderId')
        if not transaction_id:
            error_message = "Android IAP validation missing transaction ID."
            logger.error(error_message)
            raise ValidationError(error_message)

        if validation_response.get('is_canceled'):
            error_message = f'Android payment is cancelled for [{transaction_id}]'
            logger.error(error_message)
            raise UserCancelled(error_message)

        if validation_response.get('is_expired'):
            error_message = f"Android payment is expired for [{transaction_id}]"
            logger.error(error_message)
            raise PaymentError(error_message)

        payment = self._check_existing_payment(transaction_id, cart_id)

        logger.info("Android IAP validated successfully.")
        raw_response = validation_response.get('raw_response', {})
        purchase_utc_time = datetime.fromtimestamp(
            int(raw_response["purchaseTimeMillis"]) / 1000, tz=timezone.utc
        )

        return {
            'transaction_id': transaction_id,
            'created_at': purchase_utc_time,
            'payment': payment if payment else None,
            'region_code': raw_response.get('regionCode'),
        }

    def _handle_ios_validation(self, validation_response: dict, price: int, cart_id) -> dict:
        """
        Handle iOS-specific IAP validation logic.

        Args:
            validation_response (dict): The validation response from App Store.
            price (int): The expected price of the consumable product in USD.
            cart_id (str): The cart ID related to the transaction.

        Returns:
            dict: The processed validation result.
        """
        receipt = validation_response.get('receipt', {})
        in_app_purchases = receipt.get('in_app', [])

        product_sku = self.get_consumable_ios_sku(price)
        matched_purchases = [
            purchase for purchase in in_app_purchases if purchase.get('product_id') == product_sku
        ]

        if not matched_purchases:
            error_msg = f"No matching iOS IAP purchase found for SKU: {product_sku}"
            logger.error(error_msg)
            raise ValidationError(error_msg)

        latest_match_purchase = max(
            matched_purchases, key=lambda x: int(x.get('purchase_date_ms', 0))
        )

        # Update the receipt to only include the matched purchase
        receipt['in_app'] = [latest_match_purchase]
        validation_response['receipt'] = receipt

        original_transaction_id = latest_match_purchase.get('original_transaction_id')

        if 'cancellation_reason' in latest_match_purchase:
            error_message = (
                f'iOS payment is cancelled for [{original_transaction_id}] in cart [{cart_id}]'
            )
            logger.error(error_message)
            raise UserCancelled(error_message)

        payment = self._check_existing_payment(original_transaction_id, cart_id)

        return {
            'transaction_id': original_transaction_id,
            'created_at': self.parse_ios_receipt_date(
                                validation_response.get('receipt', {}).get('receipt_creation_date', '')
                            ),
            'payment': payment if payment else None,
        }


class RedundantPaymentError(Exception):
    """Exception raised for redundant payments detected."""


class ValidationError(Exception):
    """Exception raised when a payment validation fails due to invalid input or state."""


class UserCancelled(Exception):
    """Exception raised when a user manually cancels the payment process."""


class PaymentError(Exception):
    """General exception for unexpected errors during payment processing."""
