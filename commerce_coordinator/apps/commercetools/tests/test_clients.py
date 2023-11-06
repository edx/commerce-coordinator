""" Commercetools API Client(s) Testing """
import uuid

import pytest
import requests_mock
from commercetools import Client as CTClient
from commercetools.platform.models import (
    Customer,
    CustomerDraft,
    CustomerPagedQueryResponse,
    Order,
    OrderPagedQueryResponse,
    Type,
    TypeDraft
)
from conftest import TESTING_COMMERCETOOLS_CONFIG, APITestingSet, gen_example_customer, gen_order_history
from django.test import TestCase, override_settings
from utils import uuid4_str

from commerce_coordinator.apps.commercetools.catalog_info.constants import EdXFieldNames
from commerce_coordinator.apps.commercetools.catalog_info.foundational_types import TwoUCustomTypes
from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient, PaginatedResult
from commerce_coordinator.apps.core.constants import ORDER_HISTORY_PER_SYSTEM_REQ_LIMIT


class ClientTests(TestCase):
    """ CommercetoolsAPIClient Tests, please read the warning below. """
    client_set: APITestingSet

    # /!\ WARNING ==================================================================================================== #
    # The setup and teardown functions here are very strict because of how the request mocker starts and stops
    # you must delete the class instance variable if you wish to customize it in your test, and if you don't explicitly
    # delete it on teardown, the stop and start calls can get confused if the garbage collector takes a moment.
    # ---------------------------------------------------------------------------------------------------------------- #
    # NOTE: - Explicitly patched URLs will override the default matcher for their lifecycle. Ensure you 'stop' them.
    #         This can be done for you automatically by using a `with` statement as once the block ends, the mock will
    #         be stopped and destroyed by the garbage collector.
    #       - If you have a canned object from a Webservice return, it is better to explicitly add it to the backing
    #         store, if you're using a *Draft object it must go through the CTClient/CommercetoolsAPIClient, and it will
    #         be assigned an `id` and returned to you as a Non-draft object of that type.
    #       - Just like the normal CoCo API, you must have the version of the object in storage to change, all changes
    #         even those not supported by the Testing harness (like custom field changes) will still increment the
    #         version
    # /!\ WARNING ==================================================================================================== #

    def setUp(self) -> None:
        super().setUp()
        self.client_set = APITestingSet.new_instance()

    def tearDown(self) -> None:
        # force deconstructor call or some test get flaky
        del self.client_set
        super().tearDown()

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
            _ = self.client_set.client.tag_customer_with_lms_user_info(
                gen_example_customer(),
                id_num,
                "user"
            )

    def test_tag_customer_with_lms_user_id(self):
        id_num = 127
        type_val = self.client_set.client.ensure_custom_type_exists(TwoUCustomTypes.CUSTOMER_TYPE_DRAFT)
        customer = gen_example_customer()

        # The Draft converter changes the ID, so let's update our customer and draft.
        customer.custom.type.id = type_val.id

        customer_draft = CustomerDraft.deserialize(customer.serialize())

        self.client_set.backend_repo.customers.add_existing(customer)

        ret_val = self.client_set.client.tag_customer_with_lms_user_info(
            customer,
            id_num,
            "user"
        )

        self.assertEqual(ret_val.custom.type.id, type_val.id)
        # the test suite cant properly update custom fields... so we should expect it to match the draft, its more
        # important we didn't throw an exception
        self.assertEqual(ret_val.custom.fields, customer_draft.custom.fields)
        # At-least we know a change was tracked, even if the testing utils ignore the actual one
        self.assertEqual(ret_val.version, customer.version + 1)

    def test_get_customer_by_lms_user_id_user_missing(self):
        base_url = self.client_set.get_base_url_from_client()
        id_num = 127
        _ = self.client_set.client.ensure_custom_type_exists(TwoUCustomTypes.CUSTOMER_TYPE_DRAFT)

        limit = 2
        # Because the base mocker can't do param binding, we have to intercept.
        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.get(
                f"{base_url}customers?"
                f"where=custom%28fields%28edx-lms_user_id%3D%3Aid%29%29"
                f"&limit={limit}"
                f"&var.id={id_num}",
                json=CustomerPagedQueryResponse(
                    limit=limit, count=0, total=0, offset=0,
                    results=[],
                ).serialize()
            )
            ret_val = self.client_set.client.get_customer_by_lms_user_id(id_num)

            self.assertIsNone(ret_val)

    def test_get_customer_by_lms_user_id(self):
        base_url = self.client_set.get_base_url_from_client()
        id_num = 127
        type_val = self.client_set.client.ensure_custom_type_exists(TwoUCustomTypes.CUSTOMER_TYPE_DRAFT)
        customer = gen_example_customer()
        customer.custom.fields[EdXFieldNames.LMS_USER_ID] = f"{id_num}"

        # The Draft converter changes the ID, so let's update our customer and draft.
        customer.custom.type.id = type_val.id

        self.client_set.backend_repo.customers.add_existing(customer)

        limit = 2
        # Because the base mocker can't do param binding, we have to intercept.
        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.get(
                f"{base_url}customers?"
                f"where=custom%28fields%28edx-lms_user_id%3D%3Aid%29%29"
                f"&limit={limit}"
                f"&var.id={id_num}",
                json=CustomerPagedQueryResponse(
                    limit=limit, count=1, total=1, offset=0,
                    results=self.client_set.fetch_from_storage('customer', Customer),
                ).serialize()
            )

            ret_val = self.client_set.client.get_customer_by_lms_user_id(id_num)

            self.assertEqual(ret_val.custom.fields[EdXFieldNames.LMS_USER_ID], f"{id_num}")

    def test_get_customer_by_lms_user_id_should_fail_on_more_than_1(self):
        id_num = 127
        type_val = self.client_set.client.ensure_custom_type_exists(TwoUCustomTypes.CUSTOMER_TYPE_DRAFT)
        customer = gen_example_customer()
        customer.custom.fields[EdXFieldNames.LMS_USER_ID] = id_num

        # The Draft converter changes the ID, so let's update our customer and draft.
        customer.custom.type.id = type_val.id

        self.client_set.backend_repo.customers.add_existing(customer)
        customer.id = uuid4_str()
        customer.email = "someone@somesite.text"
        customer.customer_number = "blah"
        self.client_set.backend_repo.customers.add_existing(customer)

        # the query/where in the test cases doesn't support custom field names, so it returns everything.
        with pytest.raises(ValueError) as _:
            _ = self.client_set.client.get_customer_by_lms_user_id(id_num)

    def test_order_history_throws_if_user_not_found(self):
        with pytest.raises(ValueError) as _:
            _ = self.client_set.client.get_orders_for_customer(995)

    def test_get_customer_by_lms_user_id_double(self):
        base_url = self.client_set.get_base_url_from_client()
        id_num = 127
        type_val = self.client_set.client.ensure_custom_type_exists(TwoUCustomTypes.CUSTOMER_TYPE_DRAFT)
        customer = gen_example_customer()
        customer.custom.fields[EdXFieldNames.LMS_USER_ID] = id_num

        # The Draft converter changes the ID, so let's update our customer and draft.
        customer.custom.type.id = type_val.id

        self.client_set.backend_repo.customers.add_existing(customer)

        # Because the base mocker can't do param binding, we have to intercept.
        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.get(
                f"{base_url}customers?"
                f"where=custom%28fields%28edx-lms_user_id%3D%3Aid%29%29"
                f"&limit=2"
                f"&var.id={id_num}",
                json=CustomerPagedQueryResponse(
                    limit=2, count=2, total=2, offset=0,
                    results=self.client_set.fetch_from_storage('customer', Customer) +
                            self.client_set.fetch_from_storage('customer', Customer),
                ).serialize()
            )

            with pytest.raises(ValueError) as _:
                _ = self.client_set.client.get_customer_by_lms_user_id(id_num)

    def test_order_history(self):
        base_url = self.client_set.get_base_url_from_client()
        id_num = 127
        type_val = self.client_set.client.ensure_custom_type_exists(TwoUCustomTypes.CUSTOMER_TYPE_DRAFT)
        customer = gen_example_customer()
        orders = gen_order_history()
        customer.custom.fields[EdXFieldNames.LMS_USER_ID] = id_num

        # The Draft converter changes the ID, so let's update our customer and draft.
        customer.custom.type.id = type_val.id

        self.client_set.backend_repo.customers.add_existing(customer)

        for order in orders:
            order.customer_id = customer.id
            self.client_set.backend_repo.orders.add_existing(order)

        limit = ORDER_HISTORY_PER_SYSTEM_REQ_LIMIT

        # Because the base mocker can't do param binding, we have to intercept.
        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.get(
                f"{base_url}customers?"
                f"where=custom%28fields%28edx-lms_user_id%3D%3Aid%29%29"
                f"&limit=2"
                f"&var.id={id_num}",
                json=CustomerPagedQueryResponse(
                    limit=limit, count=1, total=1, offset=0,
                    results=self.client_set.fetch_from_storage('customer', Customer),
                ).serialize()
            )
            mocker.get(
                f"{base_url}orders?"
                f"where=customerId%3D%3Acid&"
                f"limit={limit}&"
                f"offset=0&"
                f"sort=completedAt+desc&"
                f"var.cid={customer.id}",
                json=OrderPagedQueryResponse(
                    limit=limit, count=1, total=1, offset=0,
                    results=self.client_set.fetch_from_storage('order', Order),
                ).serialize()
            )

            ret_orders = self.client_set.client.get_orders_for_customer(id_num)
            self.assertEqual(ret_orders[0].total, len(orders))
            self.assertEqual(ret_orders[0].offset, 0)

    def test_order_history_with_limits(self):
        base_url = self.client_set.get_base_url_from_client()
        id_num = 127
        type_val = self.client_set.client.ensure_custom_type_exists(TwoUCustomTypes.CUSTOMER_TYPE_DRAFT)
        customer = gen_example_customer()
        orders = gen_order_history(3)
        customer.custom.fields[EdXFieldNames.LMS_USER_ID] = id_num

        # The Draft converter changes the ID, so let's update our customer and draft.
        customer.custom.type.id = type_val.id

        self.client_set.backend_repo.customers.add_existing(customer)

        for order in orders:
            order.customer_id = customer.id
            self.client_set.backend_repo.orders.add_existing(order)

        params = {
            'limit': 2,
            'offset': 0,
            'total': len(orders)
        }

        # Because the base mocker can't do param binding, we have to intercept.
        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.get(
                f"{base_url}customers?"
                f"where=custom%28fields%28edx-lms_user_id%3D%3Aid%29%29"
                f"&limit=2"
                f"&var.id={id_num}",
                json=CustomerPagedQueryResponse(
                    limit=2, count=1, total=1, offset=0,
                    results=self.client_set.fetch_from_storage('customer', Customer),
                ).serialize()
            )
            mocker.get(
                f"{base_url}orders?"
                f"where=customerId%3D%3Acid&"
                f"limit={params['limit']}&"
                f"offset={params['offset']}&"
                f"sort=completedAt+desc&"
                f"var.cid={customer.id}",
                json=OrderPagedQueryResponse(
                    limit=params['limit'], count=params['limit'], total=params['total'], offset=params['offset'],
                    results=self.client_set.fetch_from_storage('order', Order)[:2],
                ).serialize()
            )

            ret_orders = self.client_set.client.get_orders_for_customer(id_num, limit=params['limit'],
                                                                        offset=params['offset'])

            self.assertEqual(ret_orders[0].total, len(orders))
            self.assertEqual(ret_orders[0].has_more(), True)
            self.assertEqual(ret_orders[0].next_offset(), params['limit'])
            self.assertEqual(ret_orders[0].offset, params['offset'])


class PaginatedResultsTest(TestCase):
    def test_data_class_does_have_more(self):
        data = [i for i in range(0, 11)]
        paginated = PaginatedResult(data[:10], len(data), 0)

        self.assertEqual(paginated.has_more(), True)
        self.assertEqual(paginated.next_offset(), 10)

    def test_data_class_doesnt_have_more(self):
        data = [i for i in range(0, 10)]
        paginated = PaginatedResult(data, len(data), 0)

        self.assertEqual(paginated.has_more(), False)
        self.assertEqual(paginated.next_offset(), 10)
