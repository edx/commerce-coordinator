""" Commercetools API Client(s) Testing """
import uuid

import pytest
from commercetools import Client as CTClient
from commercetools.platform.models import Customer, CustomerDraft, Type, TypeDraft

from commerce_coordinator.apps.commercetools.catalog_info.constants import EdXFieldNames
from conftest import gen_example_customer, TESTING_COMMERCETOOLS_CONFIG, APITestingSet
from django.test import TestCase, override_settings

from commerce_coordinator.apps.commercetools.catalog_info.foundational_types import TwoUCustomTypes
from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient


class ClientTests(TestCase):
    client_set: APITestingSet

    # /!\ WARNING
    # The setup and teardown functions here are very strict because of how the request mocker starts and stops
    # you must delete the class instance variable if you wish to customize it in your test, and if you don't explicitly
    # delete it on teardown, the stop and start calls can get confused if the garbage collector takes a moment.
    # /!\ WARNING

    def setUp(self) -> None:
        super().setUp()
        self.client_set = APITestingSet.new_instance()

    def tearDown(self) -> None:
        super().tearDown()
        # force deconstructor call or some test get flaky
        del self.client_set

    @override_settings(COMMERCETOOLS_CONFIG=TESTING_COMMERCETOOLS_CONFIG)
    def test_null_api_client_using_server_config(self):
        """This function tests default client creation from Django config"""

        del self.client_set

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
                gen_example_customer(),
                id_num
            )

    def test_tag_customer_with_lms_user_id(self):
        id_num = 127
        type_val = self.client_set.client.ensure_custom_type_exists(TwoUCustomTypes.CUSTOMER_TYPE_DRAFT)
        customer = gen_example_customer()

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
        customer = gen_example_customer()
        customer.custom.fields[EdXFieldNames.LMS_USER_ID] = id_num

        # The Draft converter, changes the ID so lets update our customer and draft.
        customer.custom.type.id = type_val.id

        self.client_set.backend_repo.customers.add_existing(customer)
        ret_val = self.client_set.client.get_customer_by_lms_user_id(id_num)

        self.assertEqual(ret_val.custom.fields[EdXFieldNames.LMS_USER_ID], id_num)

    def test_get_customer_by_lms_user_id_should_fail_on_more_than_1(self):
        id_num = 127
        type_val = self.client_set.client.ensure_custom_type_exists(TwoUCustomTypes.CUSTOMER_TYPE_DRAFT)
        customer = gen_example_customer()
        customer.custom.fields[EdXFieldNames.LMS_USER_ID] = id_num

        # The Draft converter, changes the ID so lets update our customer and draft.
        customer.custom.type.id = type_val.id

        self.client_set.backend_repo.customers.add_existing(customer)
        customer.id = str(uuid.uuid4())
        customer.email = "someone@somesite.text"
        customer.customer_number = "blah"
        self.client_set.backend_repo.customers.add_existing(customer)

        # the query/where in the test cases doesnt support custom field names so it returns everything.
        with pytest.raises(ValueError) as _:
            _ = self.client_set.client.get_customer_by_lms_user_id(id_num)
