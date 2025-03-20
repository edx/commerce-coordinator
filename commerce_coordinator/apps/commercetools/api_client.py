import logging
from typing import Dict, List, Optional, Union

import requests
from django.conf import settings
from requests.exceptions import HTTPError

from commerce_coordinator.apps.commercetools.constants import BUNDLE_CART_DISCOUNT_KEY_FORMAT, CT_ABSOLUTE_DISCOUNT_TYPE


logger = logging.getLogger(__name__)


class CTCustomAPIClient:
    """Custom Commercetools API Client using requests."""

    def __init__(self):
        """
        Initialize the Commercetools client with configuration from Django settings.
        """
        self.config = settings.COMMERCETOOLS_CONFIG
        self.access_token = self._get_access_token()

    def _get_access_token(self) -> str:
        """
        Retrieve an access token using client credentials flow for Commercetools.

        Returns:
            str: Access token for API requests.
        """
        auth_url = self.config["authUrl"]
        auth = (self.config["clientId"], self.config["clientSecret"])
        data = {
            "grant_type": "client_credentials",
            "scope": self.config['scopes'],
        }

        response = requests.post(auth_url, auth=auth, data=data)
    
        response.raise_for_status()
        return response.json()["access_token"]

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json: Optional[Dict] = None,
    ) -> Union[Dict, List]:
        """
        Make an HTTP request to the Commercetools API.

        Args:
            method (str): HTTP method (e.g., "GET", "POST").
            endpoint (str): API endpoint (e.g., "/cart-discounts").
            params (Optional[Dict]): Query parameters.
            json (Optional[Dict]): JSON payload for POST/PUT requests.

        Returns:
            Union[Dict, List]: JSON response from the API or None if the request fails.
        """
        url = f"{self.config['apiUrl']}/{self.config['projectKey']}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        try:
            response = requests.request(method, url, headers=headers, params=params, json=json)
            response.raise_for_status()
            return response.json()
        except HTTPError as err:
            if response is not None:
                response_message = response.json().get('message', 'No message provided.')
                logger.error(
                    "API request for endpoint: %s failed with error: %s and message: %s",
                    endpoint, err, response_message
                )
            else:
                logger.error("API request for endpoint: %s failed with error: %s", endpoint, err)

            return None

    def get_ct_bundle_offers_without_code(self) -> Dict:
        """
        Fetch bundle cart discounts without a discount code from Commercetools.

        Args:
            failed_discounts (list): List of failed discounts.

        Returns:
            Dict: Cart discount data or None if request fails.
        """
        # This query is used to get all cart discounts for program offers.
        query_params = 'requiresDiscountCode=false and target(type="lineItems")'

        bundle_offer_without_codes = self._make_request(
            "GET",
            "cart-discounts",
            params={"where": query_params},
        )
        if not bundle_offer_without_codes:
            return None

        return bundle_offer_without_codes.get("results", [])
    
    def get_program_entitlements_skus(
        self,
        produck_key: str,
    ):
        """
        Fetch entitlement SKUs for the given program key.
        """
        params = {
            "where": f'key="{produck_key}"',
            "expand": "masterData.current.variants[*].attributes[*].value",
        }
        program = self._make_request(
            "GET",
            "products",
            params=params,
        )
        entitlement_skus = []
        results = program.get("results", [])
        if not results:
            return []

        for variants in results[0].get("masterData", {}).get("current", {}).get("variants", []):
            for attribute in variants.get("attributes", []):
                if attribute.get("name") == "ref-edx-course-entitlement":
                    product_data = attribute.get("value", {}).get("obj", {})
                    master_variant = product_data.get("masterData", {}).get("current", {}).get("masterVariant", {})
                    entitlement_skus.append(master_variant.get("sku"))

        return entitlement_skus
    
    def get_program_entitlements_stand_alone_price(
        self,
        entitlement_sku: list,
    ):
        """
        Fetch standalone prices for the given entitlement SKUs.
        """
        params = {
            "where": " or ".join([f'sku="{sku}"' for sku in entitlement_sku])
        }
        response = self._make_request(
            "GET",
            "standalone-prices",
            params=params,
        )
        return response.get("results")
