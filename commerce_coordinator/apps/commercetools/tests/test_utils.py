"""
Tests for Commerce tools utils
"""
import unittest

from braze.client import BrazeClient
from django.test import override_settings

from commerce_coordinator.apps.commercetools.utils import get_braze_client


class TestBrazeHelpers(unittest.TestCase):
    """
    Tests for Braze Utils class
    """

    @override_settings(
        BRAZE_API_KEY="braze_api_key",
        BRAZE_API_SERVER="braze_api_server"
    )
    def test_get_braze_client_with_valid_settings(self):
        braze_client = get_braze_client()

        # Assert that a BrazeClient instance is returned
        self.assertIsNotNone(braze_client)
        self.assertIsInstance(braze_client, BrazeClient)

    @override_settings(
        BRAZE_API_SERVER="braze_api_server"
    )
    def test_get_braze_client_with_missing_api_key(self):
        braze_client = get_braze_client()

        # Assert that None is returned when API key is missing
        self.assertIsNone(braze_client)

    @override_settings(
        BRAZE_API_KEY="braze_api_key",
    )
    def test_get_braze_client_with_missing_api_server(self):
        braze_client = get_braze_client()

        # Assert that None is returned when API server is missing
        self.assertIsNone(braze_client)

    def test_get_braze_client_with_missing_settings(self):
        braze_client = get_braze_client()

        # Assert that None is returned when both API key and API server are missing
        self.assertIsNone(braze_client)
