""" Commercetools Custom API Client Testing """

from unittest.mock import patch

import requests_mock
from django.test import TestCase
from requests.exceptions import HTTPError

from commerce_coordinator.apps.commercetools.http_api_client import CTCustomAPIClient


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
                f"{self.client.config['apiUrl']}/{self.client.config['projectKey']}/products", json=mock_response
            )

            response = self.client._make_request("GET", "products")  # pylint: disable=protected-access
            self.assertEqual(response, mock_response)

    def test_make_request_failure(self):
        with requests_mock.Mocker() as mocker:
            mocker.get(
                f"{self.client.config['apiUrl']}/{self.client.config['projectKey']}/products",
                status_code=404,
                json={"message": "Not Found"}
            )

            with patch("requests.Response.raise_for_status", side_effect=HTTPError("404 Client Error")):
                # pylint: disable=protected-access
                response = self.client._make_request("GET", "products")
                self.assertIsNone(response)

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
            mock_response = {
                "results": [{
                    "masterData": {
                        "current": {
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
                        }
                    }
                }]
            }
            mocker.get(
                f"{self.client.config['apiUrl']}/{self.client.config['projectKey']}/products", json=mock_response
            )

            response = self.client.get_program_variants("product_key")
            expected_response = [{
                "entitlement_sku": "entitlement_sku",
                "variant_key": "variant_key"
            }]
            self.assertEqual(response, expected_response)

    def test_get_program_entitlements_standalone_prices(self):
        with requests_mock.Mocker() as mocker:
            mock_response = {"results": [{"sku": "entitlement_sku", "price": 100}]}
            mocker.get(
                f"{self.client.config['apiUrl']}/{self.client.config['projectKey']}/standalone-prices",
                json=mock_response
            )

            response = self.client.get_program_entitlements_standalone_prices(["entitlement_sku"])
            self.assertEqual(response, mock_response["results"])
