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
            total_retries: int = 3,
            base_backoff: int = 1,
            log_info: str = "",
            url_override: Optional[str] = None
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
            log_info (str): Additional log info to be appended in error/warn logs.
            url_override (Optional[str]): Override the URL for the request.

        Returns:
            Union[Dict, None]: JSON response from the API or None if all retries fail.
        """
        url = url_override or f"{self.config['apiUrl']}/{self.config['projectKey']}/{endpoint}"
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
                        " with error: %s and message: %s, %s.",
                        endpoint, attempt_number, err, response_message, log_info
                    )
                    return None

                next_attempt = attempt_number + 1
                next_backoff = base_backoff * next_attempt
                logger.warning(
                    "CTCustomAPIClient: API request failed for endpoint: %s with error: %s and message: %s, %s. "
                    "Retrying attempt #%s in %s seconds...",
                    endpoint, err, response_message, log_info, next_attempt, next_backoff
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
            params={"where": query_params, "sort": "sortOrder desc", "offset": 0, "limit": 100},
        )
        if not bundle_offer_without_codes:
            return []

        return bundle_offer_without_codes.get("results", [])

    def get_program_variants(self, product_key: str) -> List[dict]:
        """
        Fetch program variants with entitlement for the given program key using product projections.

        Args:
            product_key (str): The program key to fetch variants for.

        Returns:
            List: List of program variants with entitlements.
        """
        if not product_key:
            raise ValueError("[get_program_variants] Missing required product_key")

        params = {
            "where": f'key="{product_key}"',
            "expand": 'variants[*].attributes[*].value',
        }

        program = self._make_request(
            "GET",
            "product-projections",
            params=params,
            log_info=f"bundle_key={product_key}",
        )

        if not program or not program.get("results"):
            return []

        variants = program["results"][0].get("variants", [])
        entitlement_products = []

        for variant in variants:
            for attribute in variant.get("attributes", []):
                if attribute.get("name") == "ref-edx-course-entitlement":
                    entitlement_obj = attribute.get("value", {}).get("obj", {})
                    master_variant = entitlement_obj.get("masterData", {}).get("current", {}).get("masterVariant", {})
                    entitlement_products.append({
                        "entitlement_sku": master_variant.get("sku"),
                        "variant_key": variant.get("key"),
                    })

        return entitlement_products

    def get_standalone_prices_for_skus(
        self,
        skus: List[str],
    ) -> List[dict]:
        """
        Fetch standalone prices for the given SKUs.

        Args:
            skus (list): List of SKUs to fetch prices for.

        Returns:
            List: List of standalone prices for the given SKUs.
        """
        params = {
            "where": " or ".join([f'sku="{sku}"' for sku in skus])
        }
        response = self._make_request(
            "GET",
            "standalone-prices",
            params=params,
        )

        return response.get("results") if response else []
