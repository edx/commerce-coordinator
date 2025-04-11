"""
API clients for commerceetool app.
"""
import logging
import time
from typing import Dict, List, Optional, Union

import requests
from django.conf import settings

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
        auth_url = f"{self.config["authUrl"]}/oauth/token"
        auth = (self.config["clientId"], self.config["clientSecret"])
        data = {
            "grant_type": "client_credentials",
            "scope": self.config['scopes'],
        }

        response = requests.post(auth_url, auth=auth, data=data, timeout=settings.REQUEST_CONNECT_TIMEOUT_SECONDS)

        response.raise_for_status()
        return response.json()["access_token"]

    def _make_request(
            self,
            method: str,
            endpoint: str,
            params: Optional[Dict] = None,
            json: Optional[Dict] = None,
            total_retries: int = 2,
            base_backoff: int = 1,
    ) -> Union[Dict, None]:
        """
        Make an HTTP request to the Commercetools API with retry logic.

        Args:
            method (str): HTTP method (e.g., "GET", "POST").
            endpoint (str): API endpoint (e.g., "/cart-discounts").
            params (Optional[Dict]): Query parameters.
            json (Optional[Dict]): JSON payload for POST/PUT requests.
            total_retries (int): Number of retries after the first attempt.
            base_backoff (int): Base backoff time in seconds.

        Returns:
            Union[Dict, None]: JSON response from the API or None if all retries fail.
        """
        url = f"{self.config['apiUrl']}/{self.config['projectKey']}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        def attempt(attempt_number: int) -> Union[Dict, List, None]:
            try:
                response = requests.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    json=json,
                    timeout=settings.REQUEST_READ_TIMEOUT_SECONDS,
                )

                response.raise_for_status()
                return response.json()
            except requests.RequestException as err:
                response = getattr(err, 'response', None)
                if response is not None:
                    try:
                        response_message = response.json().get('message', 'No message provided.')
                    except ValueError:
                        response_message = getattr(response, 'text', None) or 'No message provided.'
                else:
                    response_message = str(err)

                if attempt_number >= total_retries:
                    logger.error(
                        "CTCustomAPIClient: API request failed for endpoint: %s after attempt #%s"
                        " with error: %s and message: %s",
                        endpoint, attempt_number, err, response_message
                    )
                    return None

                next_attempt = attempt_number + 1
                next_backoff = base_backoff * next_attempt
                logger.warning(
                    "API request failed for endpoint: %s with error: %s and message: %s. "
                    "Retrying attempt #%s in %s seconds...",
                    endpoint, err, response_message, next_attempt, next_backoff
                )
                time.sleep(next_backoff)
                return attempt(next_attempt)

        return attempt(0)

    def get_ct_bundle_offers_without_code(self) -> Dict:
        """
        Fetch cart discounts without a discount code from Commercetools.

        Returns:
            List: Cart discount data list or [] if request fails.
        """
        # This query is used to get all active cart discounts for program offers.
        query_params = 'requiresDiscountCode=false and target(type="lineItems") and isActive=true'

        bundle_offer_without_codes = self._make_request(
            "GET",
            "cart-discounts",
            params={"where": query_params, "sort": "sortOrder desc"},
        )
        if not bundle_offer_without_codes:
            return []

        return bundle_offer_without_codes.get("results", [])

    def get_program_variants(
        self,
        product_key: str,
    ) -> List[dict]:
        """
        Fetch program variants with entitlement for the given program key.

        Args:
            produck_key (str): The program key to fetch variants for.

        Returns:
            List: List of program variants with entitlements.
        """
        params = {
            "where": f'key="{product_key}"',
            "expand": "masterData.current.variants[*].attributes[*].value",
        }
        program = self._make_request(
            "GET",
            "products",
            params=params,
        )
        if program is None:
            return []

        entitlement_products = []
        results = program.get("results")
        if not results:
            return []

        for variant in results[0].get("masterData", {}).get("current", {}).get("variants", []):
            for attribute in variant.get("attributes", []):
                # Fetch the SKU for the course entitlement to get price.
                if attribute.get("name") == "ref-edx-course-entitlement":
                    expanded_entitlement_obj = attribute.get("value", {}).get("obj", {})
                    master_data = expanded_entitlement_obj.get("masterData", {})
                    master_variant = master_data.get("current", {}).get("masterVariant", {})

                    entitlement_products.append({
                        "entitlement_sku": master_variant.get("sku"),
                        "variant_key": variant.get("key"),
                    })

        return entitlement_products

    def get_program_entitlements_standalone_prices(
        self,
        entitlement_skus: List[str],
    ) -> List[dict]:
        """
        Fetch standalone prices for the given entitlement SKUs.

        Args:
            entitlement_skus (list): List of entitlement SKUs to fetch prices for.

        Returns:
            List: List of standalone prices for the given entitlement SKUs.
        """
        params = {
            "where": " or ".join([f'sku="{sku}"' for sku in entitlement_skus])
        }
        response = self._make_request(
            "GET",
            "standalone-prices",
            params=params,
        )

        return response.get("results") if response else []
