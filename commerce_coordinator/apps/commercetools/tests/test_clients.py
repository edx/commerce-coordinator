""" Commercetools API Client(s) Testing """
import pytest
from commercetools import Client as CTClient
from commercetools.platform.models import Customer, CustomerDraft, Type, TypeDraft

from commerce_coordinator.apps.commercetools.catalog_info.constants import EdXFieldNames
from conftest import EXAMPLE_CUSTOMER, TESTING_COMMERCETOOLS_CONFIG, APITestingSet
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

    def test_tag_customer_with_lms_user_id_should_fail_bad_type(self):
        id_num = 127

        with pytest.raises(ValueError) as _:
            _ = self.client_set.client.ensure_custom_type_exists(TwoUCustomTypes.CUSTOMER_TYPE_DRAFT)
            _ = self.client_set.client.tag_customer_with_lms_user_id(
                EXAMPLE_CUSTOMER,
                id_num
            )

    def test_tag_customer_with_lms_user_id(self):
        id_num = 127
        type_val = self.client_set.client.ensure_custom_type_exists(TwoUCustomTypes.CUSTOMER_TYPE_DRAFT)
        customer = EXAMPLE_CUSTOMER

        # The Draft converter, changes the ID so lets update our customer and draft.
        customer.custom.type.id = type_val.id

        customer_draft = CustomerDraft.deserialize(customer.serialize())

        self.client_set.backend_repo.customers.add_existing(customer)

        ret_val = self.client_set.client.tag_customer_with_lms_user_id(
            customer,
            id_num
        )

        self.assertEqual(ret_val.custom.type.id, type_val.id)
        # the test suite cant properly update custom fields... so we should expect it to match the draft, its more
        # important we didnt throw an exception
        self.assertEqual(ret_val.custom.fields, customer_draft.custom.fields)
        # Atleast we know a change was tracked, even if the testing utils ignore the actual one
        self.assertEqual(ret_val.version, customer.version + 1)

    def test_get_customer_by_lms_user_id(self):
        id_num = 127
        type_val = self.client_set.client.ensure_custom_type_exists(TwoUCustomTypes.CUSTOMER_TYPE_DRAFT)
        customer = EXAMPLE_CUSTOMER
        customer.custom.fields[EdXFieldNames.LMS_USER_ID] = id_num

        # The Draft converter, changes the ID so lets update our customer and draft.
        customer.custom.type.id = type_val.id

        self.client_set.backend_repo.customers.add_existing(customer)
        ret_val = self.client_set.client.get_customer_by_lms_user_id(id_num)

        self.assertEqual(ret_val.custom.fields[EdXFieldNames.LMS_USER_ID], id_num)
