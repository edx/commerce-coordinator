import logging
from commerce_coordinator.apps.iap.api.v1.google_validator import GooglePlayValidator
from commerce_coordinator.apps.iap.api.v1.ios_validator import IOSValidator

logger = logging.getLogger(__name__)


class IAPPaymentProcessor:
    def __init__(self, platform: str):
        self.platform = platform.lower()
        if self.platform == 'android':
            self.validator = GooglePlayValidator()
            self.NAME = 'android-iap'
        elif self.platform == 'ios':
            self.validator = IOSValidator()
            self.NAME = 'ios-iap'
        else:
            raise ValueError(f"Unsupported platform: {self.platform}")

    def validate_iap(self, cart, purchase_token: str) -> dict:
        """
        Validates IAP (In-App Purchase) based on the platform (Android/iOS).
        """
        product_sku = self.get_product_sku(cart)
        validation_response = self.validator.validate(purchase_token, product_sku)

        if 'error' in validation_response:
            logger.error("Validation failed for %s IAP: %s", self.NAME, validation_response['error'])
            return validation_response

        # Platform-specific validation checks
        if self.platform == 'android':
            return self._handle_android_validation(validation_response)
        elif self.platform == 'ios':
            return self._handle_ios_validation(validation_response, product_sku)

    def _handle_android_validation(self, validation_response: dict) -> dict:
        """
        Handle Android-specific IAP validation logic.
        """
        if validation_response.get('is_canceled'):
            logger.warning("Android IAP payment is canceled.")
            return {'error': 'Payment canceled'}

        if validation_response.get('is_expired'):
            logger.warning("Android IAP payment is expired.")
            return {'error': 'Payment expired'}

        transaction_id = validation_response.get('raw_response', {}).get('orderId')
        if not transaction_id:
            logger.error("Android IAP validation missing transaction ID.")
            return {'error': 'Invalid transaction ID'}

        logger.info("Android IAP validated successfully.")
        return {
            'transaction_id': transaction_id,
            'validation_response': validation_response
        }

    def _handle_ios_validation(self, validation_response: dict, product_sku: str) -> dict:
        """
        Handle iOS-specific IAP validation logic.
        """
        receipt = validation_response.get('receipt', {})
        in_app_purchases = receipt.get('in_app', [])

        # Find the specific purchase for the product SKU
        matched_purchase = None
        for purchase in in_app_purchases:
            if purchase.get('product_id') == product_sku:
                matched_purchase = purchase
                break

        if not matched_purchase:
            logger.error("No matching iOS IAP purchase found for SKU: %s", product_sku)
            return {'error': 'No matching purchase found'}

        # Update the receipt to only include the matched purchase
        receipt['in_app'] = [matched_purchase]
        validation_response['receipt'] = receipt

        original_transaction_id = matched_purchase.get('original_transaction_id')
        if not original_transaction_id:
            logger.error("iOS IAP validation missing original transaction ID.")
            return {'error': 'Invalid transaction ID'}

        # Check for cancellation
        if 'cancellation_reason' in matched_purchase:
            logger.warning("iOS IAP payment is canceled.")
            return {'error': 'Payment canceled'}

        logger.info("iOS IAP validated successfully.")
        return {
            'transaction_id': original_transaction_id,
            'validation_response': validation_response
        }

    def get_product_sku(self, cart):
        """
        Retrieve the product SKU from the cart.
        Modify this method to match your SKU logic.
        """
        return cart.line_items[0].sku if cart.line_items else ""

    def is_payment_redundant(self, transaction_id=None, original_transaction_id=None):
        """
        Check if the payment is redundant (processed before).
        """
        from ecommerce.extensions.payment.models import PaymentProcessorResponse

        if self.platform == 'android':
            return PaymentProcessorResponse.objects.filter(
                processor_name=self.NAME,
                transaction_id=transaction_id
            ).exists()
        elif self.platform == 'ios':
            return PaymentProcessorResponse.objects.filter(
                processor_name=self.NAME,
                extension__original_transaction_id=original_transaction_id
            ).exists()
