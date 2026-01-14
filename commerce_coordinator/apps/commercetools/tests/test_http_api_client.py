""" Commercetools Custom API Client Testing """

from unittest.mock import patch

import requests_mock
from django.test import TestCase
from edx_django_utils.cache import TieredCache
from requests import Response
from requests.exceptions import HTTPError

from commerce_coordinator.apps.commercetools.http_api_client import CTCustomAPIClient
from commerce_coordinator.apps.core.memcache import safe_key


class TestCTCustomAPIClient(TestCase):
    """Test cases for the Commercetools Custom API Client."""

    def setUp(self):
        self.get_access_token_patcher = patch.object(
            CTCustomAPIClient, "_get_access_token", return_value="mock_access_token"
        )
        self.mock_get_access_token = self.get_access_token_patcher.start()
        self.addCleanup(self.get_access_token_patcher.stop)
        self.client = CTCustomAPIClient()
        self.client.config = {
            "authUrl": "https://auth.commercetools.com",
            "clientId": "client_id",
            "clientSecret": "client_secret",
            "scopes": "scope",
            "apiUrl": "https://api.commercetools.com",
            "projectKey": "project_key"
        }
        self.client.access_token = "mock_access_token"
        self.mock_product_projections_response = {
            "results": [{
                "variants": [{
                    "key": "variant_key",
                    "attributes": [{
                        "name": "ref-edx-course-entitlement",
                        "value": {
                            "obj": {
                                "masterData": {
                                    "current": {
                                        "masterVariant": {
                                            "sku": "entitlement_sku"
                                        }
                                    }
                                }
                            }
                        }
                    }]
                }]
            }]
        }
        self.get_program_variants_cache_key = safe_key(
            key='product_key', key_prefix='commercetools_get_program_variants', version='1'
        )

    def tearDown(self):
        super().tearDown()
        TieredCache.dangerous_clear_all_tiers()

    def test_get_access_token(self):
        with requests_mock.Mocker() as mocker:
            mock_response = {"access_token": "mock_access_token"}
            mocker.post(f"{self.client.config['authUrl']}/oauth/token", json=mock_response)

            access_token = self.client._get_access_token()  # pylint: disable=protected-access
            self.assertEqual(access_token, "mock_access_token")

    def test_make_request_success(self):
        with requests_mock.Mocker() as mocker:
            mock_response = {"results": [{"id": "mock_id"}]}
            mocker.get(
                f"{self.client.config['apiUrl']}/{self.client.config['projectKey']}/product-projections",
                json=mock_response
            )

            response = self.client._make_request("GET", "product-projections")  # pylint: disable=protected-access
            self.assertEqual(response, mock_response)

    def test_make_request_failure(self):
        with requests_mock.Mocker() as mocker:
            mocker.get(
                f"{self.client.config['apiUrl']}/{self.client.config['projectKey']}/product-projections",
                status_code=404,
                json={"message": "Not Found"}
            )

            with patch("requests.Response.raise_for_status", side_effect=HTTPError("404 Client Error")):
                # pylint: disable=protected-access
                response = self.client._make_request("GET", "product-projections")
                self.assertIsNone(response)

    def test_make_request_retries_and_fails(self):
        """Test that the function retries the correct number of times and fails."""
        with requests_mock.Mocker() as mocker, patch("time.sleep", return_value=None) as mock_sleep:
            mocker.get(
                f"{self.client.config['apiUrl']}/{self.client.config['projectKey']}/product-projections",
                status_code=502,
                json={"message": "Bad Gateway"}
            )

            with patch("requests.Response.raise_for_status", side_effect=HTTPError("502 Bad Gateway")):
                # pylint: disable=protected-access
                response = self.client._make_request("GET", "product-projections")
                self.assertIsNone(response)

            self.assertEqual(mock_sleep.call_count, 3)  # 3 retries

    def test_make_request_retries_and_succeeds(self):
        """Test that the function retries and eventually succeeds."""
        with requests_mock.Mocker() as mocker, patch("time.sleep", return_value=None) as mock_sleep:
            # Simulate failure on the first attempt and success on the second
            mocker.get(
                f"{self.client.config['apiUrl']}/{self.client.config['projectKey']}/product-projections",
                [
                    {"status_code": 500, "json": {"message": "Internal Server Error"}},
                    {"status_code": 200, "json": {"results": [{"id": "mock_id"}]}},
                ]
            )

            response = self.client._make_request("GET", "product-projections")  # pylint: disable=protected-access
            self.assertIsNotNone(response)
            self.assertEqual(response, {"results": [{"id": "mock_id"}]})

            self.assertEqual(mock_sleep.call_count, 1)  # 1 retry

    @patch("commerce_coordinator.apps.commercetools.http_api_client.logger.error")
    def test_make_request_response_json_throws_value_error(self, mock_logger):
        """Test that the function handles ValueError when response.json() raises an exception."""
        with requests_mock.Mocker() as mocker, patch("time.sleep", return_value=None):
            url = f"{self.client.config['apiUrl']}/{self.client.config['projectKey']}/product-projections"

            mocker.get(
                url,
                status_code=502,
                text="Bad Gateway",
            )

            bad_response = Response()
            bad_response.status_code = 502
            error_with_response = HTTPError("502 Bad Gateway")
            error_with_response.response = bad_response

            with patch("requests.Response.raise_for_status", side_effect=error_with_response):
                # pylint: disable=protected-access
                self.client._make_request("GET", "product-projections")

                mock_logger.assert_called_with(
                    "CTCustomAPIClient: API request failed for endpoint: %s after attempt #%s with "
                    "error: %s and message: %s, %s.",
                    "product-projections",
                    3,
                    error_with_response,
                    'No message provided.',
                    ''
                )

                # expects that ValueError is handled properly and
                # Verify that 'No message provided.' was part of the log
                log_message = mock_logger.call_args[0][4]
                self.assertIn("No message provided.", str(log_message))

    def test_get_ct_bundle_offers_without_code(self):
        with requests_mock.Mocker() as mocker:
            mock_response = {"results": [{"id": "mock_id"}]}
            mocker.get(
                f"{self.client.config['apiUrl']}/{self.client.config['projectKey']}/cart-discounts", json=mock_response
            )

            response = self.client.get_ct_bundle_offers_without_code()
            self.assertEqual(response, mock_response["results"])

    def test_get_program_variants(self):
        with requests_mock.Mocker() as mocker:
            mocker.get(
                f"{self.client.config['apiUrl']}/{self.client.config['projectKey']}/product-projections",
                json=self.mock_product_projections_response
            )

            response = self.client.get_program_variants('product_key')
            expected_response = [{
                "entitlement_sku": "entitlement_sku",
                "variant_key": "variant_key"
            }]
            self.assertEqual(response, expected_response)

    def test_get_program_variants_failed(self):
        with requests_mock.Mocker() as mocker:
            mocker.get(
                f"{self.client.config['apiUrl']}/{self.client.config['projectKey']}/product-projections",
                json=None
            )

            response = self.client.get_program_variants('product_key')
            expected_response = []
            self.assertEqual(response, expected_response)
            # don't cache failed response
            self.assertFalse(TieredCache.get_cached_response(self.get_program_variants_cache_key).is_found)

    def test_get_program_variants_no_results(self):
        with requests_mock.Mocker() as mocker:
            mocker.get(
                f"{self.client.config['apiUrl']}/{self.client.config['projectKey']}/product-projections",
                json={"results": []}
            )

            response = self.client.get_program_variants('product_key')
            self.assertEqual(response, [])
            self.assertEqual(
                response, TieredCache.get_cached_response(self.get_program_variants_cache_key).get_value_or_default([])
            )

    def test_get_program_variants_cache(self):
        with requests_mock.Mocker() as mocker:
            # pylint: disable-next=protected-access
            with patch.object(self.client, '_make_request', wraps=self.client._make_request) as wrapped_request:
                product_key = 'product_key'
                mocker.get(
                    f"{self.client.config['apiUrl']}/{self.client.config['projectKey']}/product-projections",
                    json=self.mock_product_projections_response
                )

                response = self.client.get_program_variants(product_key)
                expected_response = [{
                    "entitlement_sku": "entitlement_sku",
                    "variant_key": "variant_key"
                }]
                self.assertEqual(response, expected_response)
                self.assertEqual(
                    response,
                    TieredCache.get_cached_response(self.get_program_variants_cache_key).get_value_or_default([])
                )

                # return cached response even if CT response changes
                mocker.get(
                    f"{self.client.config['apiUrl']}/{self.client.config['projectKey']}/product-projections",
                    json=None
                )
                response = self.client.get_program_variants(product_key)
                wrapped_request.assert_called_once()
                self.assertEqual(response, expected_response)

    def test_get_standalone_prices_for_skus(self):
        with requests_mock.Mocker() as mocker:
            mock_response = {"results": [{"sku": "entitlement_sku", "price": 100}]}
            mocker.get(
                f"{self.client.config['apiUrl']}/{self.client.config['projectKey']}/standalone-prices",
                json=mock_response
            )

            response = self.client.get_standalone_prices_for_skus(["entitlement_sku"])
            self.assertEqual(response, mock_response["results"])
