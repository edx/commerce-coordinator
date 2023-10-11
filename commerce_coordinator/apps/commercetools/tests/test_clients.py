""" Commercetools API Client(s) Testing """
from commercetools import Client as CTClient
from commercetools.platform.models import Type, TypeDraft
from conftest import TESTING_COMMERCETOOLS_CONFIG, APITestingSet
from django.test import TestCase, override_settings

from commerce_coordinator.apps.commercetools.catalog_info.foundational_types import TwoUCustomTypes
from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient


class ClientTests(TestCase):
    client_set: APITestingSet

    def setUp(self) -> None:
        super().setUp()
        self.client_set = APITestingSet.new_instance()

    @override_settings(COMMERCETOOLS_CONFIG=TESTING_COMMERCETOOLS_CONFIG)
    def test_null_api_client_using_server_config(self):
        """This function tests default client creation from Django config"""

        # When this runs it shouldn't throw an exception
        self.client_set = APITestingSet.new_instance(lambda: CommercetoolsAPIClient())
        self.assertIsNotNone(self.client_set.client)
        self.assertIsInstance(self.client_set.client, CommercetoolsAPIClient)
        self.assertIsInstance(self.client_set.client.base_client, CTClient)

    def test_ensure_custom_type_exists(self):
        draft = TwoUCustomTypes.CUSTOMER_TYPE_DRAFT

        self.assertIsInstance(draft, TypeDraft)

        ret_val = self.client_set.client.ensure_custom_type_exists(draft)

        self.assertIsInstance(ret_val, Type)
        self.assertEqual(ret_val.key, draft.key)
