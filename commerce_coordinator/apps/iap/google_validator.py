"""
Google Play Validator Module for In-App Purchase (IAP) Validation.

This module provides functionality for validating Google Play in-app purchases
using the Google Play Developer API and the `google-api-python-client` library.
"""

import json
import logging
from typing import Any, Dict

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from commerce_coordinator.apps.commercetools.catalog_info.constants import ANDROID_IAP

logger = logging.getLogger(__name__)


def get_consumable_android_sku(price: int) -> str:
    """
    Returns the Google Play product ID (SKU) for the given price.

    Args:
        price (int): Price of the product in USD (integer).

    Returns:
        str: Corresponding product SKU string.
    """
    return f"mobile.android.usd{int(price)}"


class GooglePlayValidator:
    """
    A validator for Google Play In-App Purchases using Google Play's API.
    """

    def validate(self, purchase_token: str, price: int) -> Dict[str, Any]:
        """
        Validates the purchase token with Google Play Developer API.

        Args:
            purchase_token (str): The purchase token received from the client.
            price (int): The purchase price in USD to derive the SKU.

        Returns:
            dict: A dictionary containing the raw API response and status flags.
        """
        configuration = settings.PAYMENT_PROCESSOR_CONFIG["edx"][ANDROID_IAP]
        bundle_id = configuration.get("google_bundle_id")
        service_account_info = configuration.get("google_service_account_key_file")
        if isinstance(service_account_info, str):
            service_account_info = json.loads(service_account_info)
        product_id = get_consumable_android_sku(price)
        scope = configuration.get("google_publisher_api_scope")

        if not bundle_id or not service_account_info:
            logger.error("Google Play configuration missing 'google_bundle_id' or 'google_service_account_key_file'.")
            raise ImproperlyConfigured("Google Play configuration is incomplete.")

        try:
            credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=[scope]
            )
            service = build("androidpublisher", "v3", credentials=credentials)

            request = service.purchases().products().get(  # pylint: disable=no-member
                packageName=bundle_id,
                productId=product_id,
                token=purchase_token
            )
            response = request.execute()

            is_canceled = response.get("purchaseState") == 1  # 0 = purchased, 1 = canceled
            is_expired = False  # Expiry check not applicable for one-time products

            return {
                "raw_response": response,
                "is_canceled": is_canceled,
                "is_expired": is_expired
            }

        except HttpError as e:
            logger.error("Google Play validation failed: %s", e)
            return {
                "error": str(e),
                "message": getattr(e, 'reason', 'Unknown HTTP error')
            }

        except Exception as e:  # pylint: disable=broad-except
            logger.exception("Unexpected error during Google Play validation.")
            return {
                "error": str(e),
                "message": "Unexpected error occurred"
            }
