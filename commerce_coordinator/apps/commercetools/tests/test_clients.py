""" Commercetools API Client(s) Testing """

from datetime import datetime
import pytest
import requests_mock
import stripe
from commercetools import CommercetoolsError
from commercetools.platform.models import (
    Customer,
    CustomerDraft,
    CustomerPagedQueryResponse,
    CustomObject,
    Order,
    OrderPagedQueryResponse,
    ReturnInfo,
    ReturnPaymentState,
    ReturnShipmentState,
    TransactionState,
    TransactionType,
    Type as CustomType,
    TypeDraft as CustomTypeDraft,
)
from django.test import TestCase
from mock import patch
from openedx_filters.exceptions import OpenEdxFilterException

from commerce_coordinator.apps.commercetools.catalog_info.constants import EdXFieldNames, TwoUKeys
from commerce_coordinator.apps.commercetools.catalog_info.foundational_types import TwoUCustomTypes
from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient, PaginatedResult
from commerce_coordinator.apps.commercetools.tests.conftest import (
    DEFAULT_EDX_LMS_USER_ID,
    APITestingSet,
    MonkeyPatch,
    gen_cart,
    gen_customer,
    gen_example_customer,
    gen_line_item_state,
    gen_order,
    gen_order_history,
    gen_payment,
    gen_payment_with_multiple_transactions,
    gen_retired_customer,
    gen_return_item
)
from commerce_coordinator.apps.commercetools.tests.sub_messages.test_tasks import CommercetoolsAPIClientMock
from commerce_coordinator.apps.core.constants import ORDER_HISTORY_PER_SYSTEM_REQ_LIMIT
from commerce_coordinator.apps.core.tests.utils import uuid4_str


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

    def test_ensure_custom_type_exists(self):
        draft = TwoUCustomTypes.CUSTOMER_TYPE_DRAFT

        self.assertIsInstance(draft, CustomTypeDraft)

        ret_val = self.client_set.client.ensure_custom_type_exists(draft)

        self.assertIsInstance(ret_val, CustomType)
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

    def test_get_order_by_id(self):
        base_url = self.client_set.get_base_url_from_client()
        order_id = "mock_order_id"
        expected_order = gen_order(order_id)

        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.get(
                f"{base_url}orders/{order_id}",
                json=expected_order.serialize()
            )

            result = self.client_set.client.get_order_by_id(order_id)
            self.assertEqual(result, expected_order)

    def test_get_order_by_number(self):
        base_url = self.client_set.get_base_url_from_client()
        expected_order = gen_order("mock_order_id")
        order_number = expected_order.order_number

        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.get(
                f"{base_url}orders/order-number={order_number}",
                json=expected_order.serialize()
            )

            result = self.client_set.client.get_order_by_number(order_number)
            self.assertEqual(result, expected_order)

    def test_get_customer_by_id(self):
        base_url = self.client_set.get_base_url_from_client()
        expected_customer = gen_example_customer()
        customer_id = expected_customer.id

        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.get(
                f"{base_url}customers/{customer_id}",
                json=expected_customer.serialize()
            )

            result = self.client_set.client.get_customer_by_id(customer_id)
            self.assertEqual(result, expected_customer)

    def test_get_state_by_key(self):
        base_url = self.client_set.get_base_url_from_client()
        state_key = '2u-fulfillment-pending-state'
        expected_state = gen_line_item_state()

        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.get(
                f"{base_url}states/key={state_key}",
                json=expected_state.serialize()
            )

            result = self.client_set.client.get_state_by_key(state_key)
            self.assertEqual(result, expected_state)

    def test_get_state_by_id(self):
        base_url = self.client_set.get_base_url_from_client()
        expected_state = gen_line_item_state()
        state_id = expected_state.id

        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.get(
                f"{base_url}states/{state_id}",
                json=expected_state.serialize()
            )

            result = self.client_set.client.get_state_by_id(state_id)
            self.assertEqual(result, expected_state)

    def test_get_payment_by_key(self):
        base_url = self.client_set.get_base_url_from_client()
        payment_key = "pi_4MtwBwLkdIwGlenn28a3tqPa"
        expected_payment = gen_payment()

        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.get(
                f"{base_url}payments/key={payment_key}",
                json=expected_payment.serialize()
            )

            result = self.client_set.client.get_payment_by_key(payment_key)
            self.assertEqual(result.id, expected_payment.id)

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
                    results=(self.client_set.fetch_from_storage('customer', Customer) +
                             self.client_set.fetch_from_storage('customer', Customer)),
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

    def test_create_return_for_order_success(self):
        base_url = self.client_set.get_base_url_from_client()

        # Mocked expected order recieved after CT SDK call to update the order
        mock_response_order = gen_order("mock_order_id")
        mock_response_order.version = "1"
        mock_response_return_item = gen_return_item("mock_return_item_id", ReturnPaymentState.REFUNDED)
        mock_response_return_info = ReturnInfo(items=[mock_response_return_item])
        mock_response_order.return_info.append(mock_response_return_info)

        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.post(
                f"{base_url}orders/{mock_response_order.id}",
                json=mock_response_order.serialize(),
                status_code=200
            )

            result = self.client_set.client.create_return_for_order(
                mock_response_order.id,
                mock_response_order.version,
                mock_response_return_item.line_item_id
            )

            self.assertEqual(result.return_info[1].items[0].shipment_state, ReturnShipmentState.RETURNED)
            self.assertEqual(result.return_info[1].items[0].payment_state, ReturnPaymentState.REFUNDED)

    def test_create_return_for_order_exception(self):
        base_url = self.client_set.get_base_url_from_client()
        mock_error_response: CommercetoolsError = {
            "message": "Could not create return for order mock_order_id",
            "errors": [
                {
                    "code": "ConcurrentModification",
                    "message": "Object [mock_order_id] has a "
                               "different version than expected. Expected: 2 - Actual: 1.",
                },
            ],
            "response": {},
            "correlation_id": '123456'
        }

        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.post(
                f"{base_url}orders/mock_order_id",
                json=mock_error_response,
                status_code=409
            )

            with patch('commerce_coordinator.apps.commercetools.clients.logging.Logger.error') as log_mock:
                with self.assertRaises(CommercetoolsError) as cm:
                    self.client_set.client.create_return_for_order(
                        order_id="mock_order_id",
                        order_version=1,
                        order_line_item_id="mock_return_item_id"
                    )

                exception = cm.exception

                expected_message = (
                    f"[CommercetoolsError] [CommercetoolsAPIClient.create_return_for_order] "
                    f"Unable to create return for order mock_order_id "
                    f"- Correlation ID: {exception.correlation_id}, Details: {exception.errors}"
                )

                log_mock.assert_called_once_with(expected_message)

    def test_order_return_payment_state_not_refunded(self):
        base_url = self.client_set.get_base_url_from_client()

        # Mocked order to be passed in to update method
        mock_order = gen_order("mock_order_id")
        mock_order.version = "2"
        mock_return_item = gen_return_item("mock_return_item_id", ReturnPaymentState.INITIAL)
        mock_return_info = ReturnInfo(items=[mock_return_item])
        mock_order.return_info.append(mock_return_info)

        # Mocked expected order recieved after CT SDK call to update the order
        mock_response_order = gen_order("mock_order_id")
        mock_response_order.version = "3"
        mock_response_return_item = gen_return_item("mock_return_item_id", ReturnPaymentState.NOT_REFUNDED)
        mock_response_return_info = ReturnInfo(items=[mock_response_return_item])
        mock_response_order.return_info.append(mock_response_return_info)

        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.post(
                f"{base_url}orders/mock_order_id",
                json=mock_response_order.serialize(),
                status_code=200
            )

            mocker.get(
                f"{base_url}orders/mock_order_id",
                json=mock_response_order.serialize(),
                status_code=200
            )

            result = self.client_set.client.update_return_payment_state_for_enrollment_code_purchase(
                mock_order.id,
                mock_order.version,
                [mock_response_return_item.line_item_id],
            )
            self.assertEqual(result.return_info[1].items[0].payment_state, ReturnPaymentState.NOT_REFUNDED)

    def test_successful_order_return_payment_state_update(self):
        base_url = self.client_set.get_base_url_from_client()

        # Mocked order to be passed in to update method
        mock_order = gen_order("mock_order_id")
        mock_order.version = "2"
        mock_return_item = gen_return_item("mock_return_item_id", ReturnPaymentState.INITIAL)
        mock_return_info = ReturnInfo(items=[mock_return_item])
        mock_order.return_info.append(mock_return_info)

        # Mocked expected order recieved after CT SDK call to update the order
        mock_response_order = gen_order("mock_order_id")
        mock_payment = gen_payment_with_multiple_transactions(TransactionType.CHARGE, 4900, TransactionType.REFUND,
                                                              4900)
        mock_response_order.version = "3"
        mock_response_return_item = gen_return_item("mock_return_item_id", ReturnPaymentState.REFUNDED)
        mock_response_return_info = ReturnInfo(items=[mock_response_return_item])
        mock_response_order.return_info.append(mock_response_return_info)

        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.post(
                f"{base_url}orders/mock_order_id",
                json=mock_response_order.serialize(),
                status_code=200
            )
            mocker.post(
                f"{base_url}payments/{mock_payment.id}",
                json=mock_payment.serialize(),
                status_code=200
            )
            mocker.get(
                f"{base_url}payments/key={mock_payment.id}",
                json=mock_payment.serialize(),
                status_code=200
            )
            mocker.get(
                f"{base_url}orders/mock_order_id",
                json=mock_response_order.serialize(),
                status_code=200
            )
            result = self.client_set.client.update_return_payment_state_after_successful_refund(
                mock_order.id,
                mock_order.version,
                [mock_response_return_item.line_item_id],
                {mock_response_return_item.line_item_id: uuid4_str()},
                {},
                mock_payment.id,
                uuid4_str()
            )
            self.assertEqual(result.return_info[1].items[0].payment_state, ReturnPaymentState.REFUNDED)

    def test_create_refund_transaction(self):
        base_url = self.client_set.get_base_url_from_client()

        mock_response_payment = gen_payment()
        mock_stripe_refund = stripe.Refund()
        stripe_refund_json = {
            "id": "re_1Nispe2eZvKYlo2Cd31jOCgZ",
            "amount": 4900,
            "charge": "ch_3P9RWsH4caH7G0X11toRGUJf",
            "created": 1692942318,
            "currency": "usd",
            "status": "succeeded"
        }
        mock_stripe_refund.update(stripe_refund_json)

        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.post(
                f"{base_url}payments/{mock_response_payment.id}",
                json=mock_response_payment.serialize(),
                status_code=200
            )

            result = self.client_set.client.create_return_payment_transaction(
                mock_response_payment.id,
                mock_response_payment.version,
                mock_stripe_refund
            )

            self.assertEqual(result.transactions[0].type, mock_response_payment.transactions[0].type)
            self.assertEqual(result.transactions[0].state, TransactionState.SUCCESS)

    def test_create_refund_transaction_exception(self):
        base_url = self.client_set.get_base_url_from_client()
        mock_stripe_refund = stripe.Refund()
        stripe_refund_json = {
            "id": "re_1Nispe2eZvKYlo2Cd31jOCgZ",
            "amount": 4900,
            "charge": "ch_3P9RWsH4caH7G0X11toRGUJf",
            "created": 1692942318,
            "currency": "usd",
            "status": "succeeded"
        }
        mock_stripe_refund.update(stripe_refund_json)

        mock_error_response: CommercetoolsError = {
            "message": "Could not create return for order mock_order_id",
            "errors": [
                {
                    "code": "ConcurrentModification",
                    "message": "Object [mock_order_id] has a "
                               "different version than expected. Expected: 2 - Actual: 1.",
                },
            ],
            "response": {},
            "correlation_id": '123456'
        }

        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.post(
                f"{base_url}payments/mock_payment_id",
                json=mock_error_response,
                status_code=409
            )

            with patch('commerce_coordinator.apps.commercetools.clients.logging.Logger.error') as log_mock:
                with self.assertRaises(CommercetoolsError) as cm:
                    self.client_set.client.create_return_payment_transaction(
                        payment_id="mock_payment_id",
                        payment_version=1,
                        refund=mock_stripe_refund
                    )

                exception = cm.exception

                expected_message = (
                    f"[CommercetoolsError] [CommercetoolsAPIClient.create_return_payment_transaction] "
                    f"Unable to create refund payment transaction for "
                    f"payment mock_payment_id, refund {mock_stripe_refund.id} with PSP: stripe_edx "
                    f"- Correlation ID: {exception.correlation_id}, Details: {exception.errors}"
                )

                log_mock.assert_called_once_with(expected_message)

    @patch('commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_state_by_id')
    def test_successful_order_line_item_state_update(self, mock_state_by_id):
        base_url = self.client_set.get_base_url_from_client()

        mock_order = gen_order("mock_order_id")
        mock_order.version = "2"
        mock_line_item_state = gen_line_item_state()
        mock_line_item_state.key = TwoUKeys.PROCESSING_FULFILMENT_STATE
        mock_order.line_items[0].state[0].state = mock_line_item_state

        mock_state_by_id().return_value = mock_line_item_state

        mock_response_order = gen_order("mock_order_id")
        mock_response_order.version = 3
        mock_response_line_item_state = gen_line_item_state()
        mock_response_line_item_state.id = "mock_success_id"
        mock_response_line_item_state.key = TwoUKeys.SUCCESS_FULFILMENT_STATE
        mock_response_order.line_items[0].state[0].state = mock_response_line_item_state

        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.post(
                f"{base_url}orders/{mock_response_order.id}",
                json=mock_response_order.serialize(),
                status_code=200
            )

            result = self.client_set.client.update_line_item_on_fulfillment(
                '',
                mock_order.id,
                mock_order.version,
                mock_order.line_items[0].id,
                1,
                mock_order.line_items[0].state[0].state.id,
                TwoUKeys.SUCCESS_FULFILMENT_STATE
            )

            self.assertEqual(result.line_items[0].state[0].state.id, mock_response_line_item_state.id)

    @patch('commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_state_by_id')
    def test_update_line_item_state_exception(self, mock_state_by_id):
        base_url = self.client_set.get_base_url_from_client()
        mock_state_by_id().return_value = gen_line_item_state()
        mock_error_response: CommercetoolsError = {
            "message": "Could not create return for order mock_order_id",
            "errors": [
                {
                    "code": "ConcurrentModification",
                    "message": "Object [mock_order_id] has a "
                               "different version than expected. Expected: 2 - Actual: 1."
                },
            ],
            "response": {},
            "correlation_id": "None"
        }

        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.post(
                f"{base_url}orders/mock_order_id",
                json=mock_error_response,
                status_code=409
            )

            with patch('commerce_coordinator.apps.commercetools.clients.logging.Logger.error') as log_mock:
                with self.assertRaises(CommercetoolsError):
                    self.client_set.client.update_line_item_on_fulfillment(
                        '',
                        "mock_order_id",
                        1,
                        "mock_order_line_item_id",
                        1,
                        "mock_order_line_item_state.id",
                        TwoUKeys.SUCCESS_FULFILMENT_STATE
                    )

                    expected_message = (
                        f"[CommercetoolsError] [CommercetoolsAPIClient.update_line_item_on_fulfillment] "
                        f"Unable to update LineItem "
                        f"of order mock_order_id "
                        f"From State: '2u-fulfillment-pending-state'"
                        f"To State: '2u-fulfillment-successful-state'"
                        f"And entitlement "
                        f"- Correlation ID: {mock_error_response['correlation_id']}, "
                        f"Details: {mock_error_response['errors']}"
                    )

                    log_mock.assert_called_with(expected_message)

    @patch('commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_state_by_id')
    def test_successful_order_all_line_items_state_update(self, mock_state_by_id):
        base_url = self.client_set.get_base_url_from_client()

        mock_order = gen_order("mock_order_id")
        mock_order.version = "2"
        mock_line_item_state = gen_line_item_state()
        mock_line_item_state.key = TwoUKeys.PROCESSING_FULFILMENT_STATE
        mock_order.line_items[0].state[0].state = mock_line_item_state

        mock_state_by_id().return_value = mock_line_item_state

        mock_response_order = gen_order("mock_order_id")
        mock_response_order.version = 3
        mock_response_line_item_state = gen_line_item_state()
        mock_response_line_item_state.id = "mock_success_id"
        mock_response_line_item_state.key = TwoUKeys.SUCCESS_FULFILMENT_STATE
        mock_response_order.line_items[0].state[0].state = mock_response_line_item_state

        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.post(
                f"{base_url}orders/{mock_response_order.id}",
                json=mock_response_order.serialize(),
                status_code=200
            )

            result = self.client_set.client.update_line_items_transition_state(
                mock_order.id,
                mock_order.version,
                mock_order.line_items,
                TwoUKeys.PENDING_FULFILMENT_STATE,
                TwoUKeys.SUCCESS_FULFILMENT_STATE
            )

            self.assertEqual(result.line_items[0].state[0].state.id, mock_response_line_item_state.id)

    @patch('commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_state_by_id')
    def test_update_all_line_items_state_exception(self, mock_state_by_id):
        mock_order = gen_order("mock_order_id")
        mock_order.version = "1"
        base_url = self.client_set.get_base_url_from_client()
        mock_state_by_id().return_value = gen_line_item_state()
        mock_error_response: CommercetoolsError = {
            "message": "Could not create return for order mock_order_id",
            "errors": [
                {
                    "code": "ConcurrentModification",
                    "message": "Object [mock_order_id] has a "
                               "different version than expected. Expected: 2 - Actual: 1."
                },
            ],
            "response": {},
            "correlation_id": "None"
        }

        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.post(
                f"{base_url}orders/mock_order_id",
                json=mock_error_response,
                status_code=409
            )

            with patch('commerce_coordinator.apps.commercetools.clients.logging.Logger.info') as log_mock:
                with self.assertRaises(CommercetoolsError):
                    self.client_set.client.update_line_items_transition_state(
                        mock_order.id,
                        mock_order.version,
                        mock_order.line_items,
                        TwoUKeys.PENDING_FULFILMENT_STATE,
                        TwoUKeys.SUCCESS_FULFILMENT_STATE
                    )

                    expected_message = (
                        f"[CommercetoolsError] [CommercetoolsAPIClient.update_line_items_transition_state] "
                        f"Failed to update LineItemStates "
                        f"for order ID 'mock_order_id'"
                        f"From State: '2u-fulfillment-pending-state'"
                        f"To State: '2u-fulfillment-successful-state'"
                        f"Line Item IDs: {mock_order.line_items[0].id} "
                        f"- Correlation ID: {mock_error_response['correlation_id']}, "
                        f"Details: {mock_error_response['errors']}"
                    )

                    log_mock.assert_called_with(expected_message)

    @patch('commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_state_by_id')
    @patch('commerce_coordinator.apps.commercetools.clients.CommercetoolsAPIClient.get_order_by_id')
    def test_order_line_item_in_correct_state(self, mock_order_by_id, mock_state_by_id):
        mock_order = gen_order("mock_order_id")
        mock_order.version = 3
        mock_line_item_state = gen_line_item_state()
        mock_line_item_state.key = TwoUKeys.PROCESSING_FULFILMENT_STATE
        mock_order.line_items[0].state[0].state = mock_line_item_state
        line_item_id = mock_order.line_items[0].id

        mock_state_by_id.return_value = mock_line_item_state
        mock_order_by_id.return_value = mock_order

        with patch('commerce_coordinator.apps.commercetools.clients.logging.Logger.info') as log_mock:
            result = self.client_set.client.update_line_item_on_fulfillment(
                '',
                mock_order.id,
                mock_order.version,
                line_item_id,
                1,
                mock_order.line_items[0].state[0].state.id,
                TwoUKeys.PROCESSING_FULFILMENT_STATE
            )

            expected_message = (
                f"[CommercetoolsAPIClient] - The line item {line_item_id} already has the correct state "
                f"{mock_line_item_state.key}. Not attempting to transition LineItemState for order id mock_order_id"
            )

            log_mock.assert_called_with(expected_message)
            self.assertEqual(result.id, mock_order.id)
            self.assertEqual(result.version, mock_order.version)

    def test_update_customer_with_anonymized_fields(self):
        base_url = self.client_set.get_base_url_from_client()
        mock_retired_first_name = "retired_user_b90b0331d08e19eaef586"
        mock_retired_last_name = "retired_user_b45093f6f96eac6421f8"
        mock_retired_email = "retired_user_149c01e31901998b11"
        mock_retired_lms_username = "retired_user_8d2382cd8435a1c520"

        mock_response_customer = gen_retired_customer(
            mock_retired_first_name,
            mock_retired_last_name,
            mock_retired_email,
            mock_retired_lms_username
        )

        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.post(
                f"{base_url}customers/{mock_response_customer.id}",
                json=mock_response_customer.serialize(),
                status_code=200
            )

            result = self.client_set.client.retire_customer_anonymize_fields(
                mock_response_customer.id,
                mock_response_customer.version,
                mock_retired_first_name,
                mock_retired_last_name,
                mock_retired_email,
                mock_retired_lms_username
            )

            self.assertEqual(result, mock_response_customer)

    def test_update_customer_with_anonymized_fields_exception(self):
        base_url = self.client_set.get_base_url_from_client()
        mock_retired_first_name = "retired_user_b90b0331d08e19eaef586"
        mock_retired_last_name = "retired_user_b45093f6f96eac6421f8"
        mock_retired_email = "retired_user_149c01e31901998b11"
        mock_retired_lms_username = "retired_user_8d2382cd8435a1c520"

        mock_error_response: CommercetoolsError = {
            "message": "Could not create return for order mock_order_id",
            "errors": [
                {
                    "code": "ConcurrentModification",
                    "detailedErrorMessage": "Object [mock_order_id] has a "
                                            "different version than expected. Expected: 2 - Actual: 1."
                },
            ],
            "response": {},
            "correlation_id": '123456'
        }

        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.post(
                f"{base_url}customers/mock_customer_id",
                json=mock_error_response,
                status_code=409
            )

            with patch('commerce_coordinator.apps.commercetools.clients.logging.Logger.error') as log_mock:
                with self.assertRaises(CommercetoolsError) as cm:
                    self.client_set.client.retire_customer_anonymize_fields(
                        "mock_customer_id",
                        1,
                        mock_retired_first_name,
                        mock_retired_last_name,
                        mock_retired_email,
                        mock_retired_lms_username
                    )

                exception = cm.exception

                expected_message = (
                    f"[CommercetoolsError] Unable to anonymize customer fields for customer "
                    f"with ID: mock_customer_id, after LMS retirement with "
                    f"error correlation id {exception.correlation_id} and error/s: {exception.errors}"
                )

                log_mock.assert_called_once_with(expected_message)

    def test_is_first_time_discount_eligible_success(self):
        base_url = self.client_set.get_base_url_from_client()
        email = 'email@example.com'
        code = 'discount-code'

        mock_orders = {
            "total": 1,
            "results": [
                {
                    "discountCodes": [
                        {
                            "discountCode": {
                                "obj": {
                                    "code": 'another-code'
                                }
                            }
                        }
                    ]
                }
            ]
        }

        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.get(
                f"{base_url}orders",
                json=mock_orders,
                status_code=200
            )

            result = self.client_set.client.is_first_time_discount_eligible(email, code)
            self.assertTrue(result)

    def test_is_first_time_discount_not_eligible(self):
        base_url = self.client_set.get_base_url_from_client()
        email = 'email@example.com'
        code = 'discount-code'

        mock_orders = {
            "total": 1,
            "results": [
                {
                    "discountCodes": [
                        {
                            "discountCode": {
                                "obj": {
                                    "code": code
                                }
                            }
                        }
                    ]
                }
            ]
        }

        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.get(
                f"{base_url}orders",
                json=mock_orders,
                status_code=200
            )

            result = self.client_set.client.is_first_time_discount_eligible(email, code)
            self.assertFalse(result)

    def test_is_first_time_discount_eligible_invalid_email(self):
        invalid_email = "invalid_email@example.com"
        code = 'discount-code'
        base_url = self.client_set.get_base_url_from_client()

        mock_orders = {
            "total": 0
        }

        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.get(
                f"{base_url}orders",
                json=mock_orders,
                status_code=200
            )

            result = self.client_set.client.is_first_time_discount_eligible(invalid_email, code)
            self.assertTrue(result)

    def test_create_customer(self):
        """Test creating a customer with lms user info"""
        base_url = self.client_set.get_base_url_from_client()
        email = "test@example.com"
        first_name = "John"
        lms_username = "test_user"

        mock_customer = gen_customer(email, lms_username)
        mock_result = {"customer": mock_customer.serialize()}

        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.post(
                f"{base_url}customers", json=mock_result, status_code=201
            )

            result = self.client_set.client.create_customer(
                email=email,
                first_name=first_name,
                last_name="",
                lms_user_id=DEFAULT_EDX_LMS_USER_ID,
                lms_username=lms_username,
            )

            # Verify the customer was created with correct data
            self.assertEqual(result.email, email)
            self.assertEqual(result.first_name, first_name)

            # Verify request to CT had correct structure
            request_body = mocker.last_request.json()
            self.assertEqual(request_body["email"], email)
            self.assertEqual(request_body["firstName"], first_name)
            self.assertEqual(request_body["authenticationMode"], "ExternalAuth")

            # Verify custom fields for LMS user info
            self.assertEqual(
                request_body["custom"]["type"]["key"],
                TwoUCustomTypes.CUSTOMER_TYPE_DRAFT.key,
            )
            custom_fields = request_body["custom"]["fields"]
            self.assertEqual(
                custom_fields[EdXFieldNames.LMS_USER_ID],
                str(DEFAULT_EDX_LMS_USER_ID),
            )
            self.assertEqual(
                custom_fields[EdXFieldNames.LMS_USER_NAME], lms_username
            )

    def test_update_customer(self):
        """Test updating a customer's attributes"""
        base_url = self.client_set.get_base_url_from_client()
        customer = gen_customer("old@example.com", "old_username")
        customer.id = uuid4_str()
        customer.version = 1

        updates = {
            "first_name": "Updated",
            "last_name": "Name",
            "email": "updated@example.com",
            "lms_username": "updated_username",
        }

        updated_customer = Customer.deserialize(customer.serialize())
        updated_customer.first_name = updates["first_name"]
        updated_customer.last_name = updates["last_name"]
        updated_customer.email = updates["email"]
        updated_customer.version += 1
        if updated_customer.custom and updated_customer.custom.fields:
            updated_customer.custom.fields[EdXFieldNames.LMS_USER_NAME] = updates[
                "lms_username"
            ]

        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.post(
                f"{base_url}customers/{customer.id}",
                json=updated_customer.serialize(),
                status_code=200,
            )

            result = self.client_set.client.update_customer(
                customer=customer,
                updates=updates,
            )

            # Verify customer was updated correctly
            self.assertEqual(result.first_name, updates["first_name"])
            self.assertEqual(result.last_name, updates["last_name"])
            self.assertEqual(result.email, updates["email"])

            # Verify request contained correct actions
            request_body = mocker.last_request.json()
            actions = request_body["actions"]

            # Should have one action for each update
            self.assertEqual(len(actions), 4)

            # Verify each action type and value
            action_types = [action["action"] for action in actions]
            self.assertIn("setFirstName", action_types)
            self.assertIn("setLastName", action_types)
            self.assertIn("changeEmail", action_types)
            self.assertIn("setCustomField", action_types)

    def test_get_customer_cart(self):
        """Test getting an active cart for a customer"""
        base_url = self.client_set.get_base_url_from_client()
        customer_id = uuid4_str()

        mock_cart = gen_cart(customer_id=customer_id)
        mock_response = mock_cart.serialize()

        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.get(
                f"{base_url}carts/customer-id={customer_id}",
                json=mock_response,
                status_code=200,
            )

            result = self.client_set.client.get_customer_cart(customer_id)

            # Verify cart was returned correctly
            self.assertIsNotNone(result)
            self.assertEqual(result.id, mock_cart.id)
            self.assertEqual(result.customer_id, customer_id)

    def test_delete_cart(self):
        """Test deleting a cart"""
        base_url = self.client_set.get_base_url_from_client()
        cart_id = uuid4_str()
        cart_version = 1

        mock_cart = gen_cart(cart_id=cart_id, cart_version=cart_version)
        mock_response = mock_cart.serialize()

        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.delete(
                f"{base_url}carts/{cart_id}?version={cart_version}",
                json=mock_response,
                status_code=200,
            )

            result = self.client_set.client.delete_cart(mock_cart)

            # Verify delete request was made
            self.assertTrue(mocker.called)
            self.assertEqual(result, None)

    def test_get_new_order_number(self):
        """Test getting a new order number"""
        base_url = self.client_set.get_base_url_from_client()
        current_year = datetime.now().year

        custom_object = CustomObject(
            id=uuid4_str(),
            version=1,
            container=TwoUKeys.ORDER_NUMBER_CUSTOM_OBJECT_CONTAINER,
            key=TwoUKeys.ORDER_NUMBER_CUSTOM_OBJECT_KEY,
            value=42,
            created_at=datetime.now(),
            last_modified_at=datetime(current_year, 1, 1),
        )

        updated_custom_object = CustomObject(
            id=custom_object.id,
            version=2,
            container=custom_object.container,
            key=custom_object.key,
            value=43,
            created_at=custom_object.created_at,
            last_modified_at=datetime.now(),
        )

        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.get(
                f"{base_url}custom-objects/"
                f"{TwoUKeys.ORDER_NUMBER_CUSTOM_OBJECT_CONTAINER}/"
                f"{TwoUKeys.ORDER_NUMBER_CUSTOM_OBJECT_KEY}",
                json=custom_object.serialize(),
                status_code=200,
            )

            mocker.post(
                f"{base_url}custom-objects",
                json=updated_custom_object.serialize(),
                status_code=201,
            )

            result = self.client_set.client.get_new_order_number()

            # Verify order number format
            expected_order_number = f"2U-{current_year}000043"
            self.assertEqual(result, expected_order_number)

    def test_create_cart(self):
        """Test creating a cart"""
        base_url = self.client_set.get_base_url_from_client()
        customer = gen_customer("test@example.com", "test_user")
        customer.id = uuid4_str()
        order_number = f"2U-{datetime.now().year}000001"
        locale = {"language": "en-US", "country": "US", "currency": "USD"}

        mock_cart = gen_cart(customer_id=customer.id, customer_email=customer.email)

        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.post(
                f"{base_url}carts", json=mock_cart.serialize(), status_code=201
            )

            result = self.client_set.client.create_cart(
                customer=customer,
                order_number=order_number,
                locale=locale,
            )

            # Verify cart was created correctly
            self.assertEqual(result.id, mock_cart.id)
            self.assertEqual(result.customer_id, customer.id)

            # Verify request had correct data
            request_body = mocker.last_request.json()
            self.assertEqual(request_body["currency"], "USD")
            self.assertEqual(request_body["country"], "US")
            self.assertEqual(request_body["locale"], "en-US")
            self.assertEqual(request_body["customerId"], customer.id)
            self.assertEqual(request_body["customerEmail"], customer.email)
            self.assertEqual(
                request_body["custom"]["fields"][TwoUKeys.ORDER_ORDER_NUMBER],
                order_number,
            )

    def test_update_cart(self):
        """Test updating a cart"""
        base_url = self.client_set.get_base_url_from_client()
        cart_id = uuid4_str()
        cart_version = 1
        customer_id = uuid4_str()
        email = "user@example.com"
        expected_domain = "example.com"
        sku = "course-v1:edX+DemoX+Demo_Course"

        cart = gen_cart(
            cart_id=cart_id,
            cart_version=cart_version,
            customer_id=customer_id,
            customer_email=email
        )

        updated_cart = gen_cart(
            cart_id=cart_id,
            cart_version=cart_version + 1,
            customer_id=customer_id,
            customer_email=email
        )

        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.post(
                f"{base_url}carts/{cart_id}",
                json=updated_cart.serialize(),
                status_code=200,
            )

            result = self.client_set.client.update_cart(
                cart=cart,
                sku=sku,
                email_domain=expected_domain,
                payment_id=''
            )

            # Verify cart was updated correctly
            self.assertEqual(result.id, cart_id)
            self.assertEqual(result.version, cart_version + 1)

            # Verify request had correct actions
            request_body = mocker.last_request.json()
            actions = request_body["actions"]
            self.assertEqual(len(actions), 6)

            lineItemAction = actions[0]
            self.assertEqual(lineItemAction["action"], "addLineItem")
            self.assertEqual(lineItemAction["sku"], sku)

            customFieldAction = actions[1]
            self.assertEqual(customFieldAction["action"], "setCustomField")
            self.assertEqual(customFieldAction["name"], TwoUKeys.ORDER_EMAIL_DOMAIN)
            self.assertEqual(customFieldAction["value"], expected_domain)


class PaginatedResultsTest(TestCase):
    """Tests for the simple logic in our Paginated Results Class"""

    def test_data_class_does_have_more(self):
        data = list(range(11))
        paginated = PaginatedResult(data[:10], len(data), 0)

        self.assertEqual(paginated.has_more(), True)
        self.assertEqual(paginated.next_offset(), 10)

    def test_data_class_doesnt_have_more(self):
        data = list(range(10))
        paginated = PaginatedResult(data, len(data), 0)

        self.assertEqual(paginated.has_more(), False)
        self.assertEqual(paginated.next_offset(), 10)


class ClientUpdateReturnTests(TestCase):
    """Tests for the update_return_payment_state_after_successful_refund method"""
    client_set: APITestingSet

    def setUp(self):
        super().setUp()
        self.mock = CommercetoolsAPIClientMock()
        self.client_set = APITestingSet.new_instance()

        MonkeyPatch.monkey(
            CommercetoolsAPIClient,
            {
                '__init__': lambda _: None,
                'get_order_by_id': self.mock.get_order_by_id,
                # 'get_customer_by_id': self.mock.get_customer_by_id,
                'get_payment_by_key': self.mock.get_payment_by_key,
                'create_return_for_order': self.mock.create_return_for_order,
                'create_return_payment_transaction': self.mock.create_return_payment_transaction
            }
        )

    def tearDown(self):
        self.mock.payment_mock.side_effect = None
        MonkeyPatch.unmonkey(CommercetoolsAPIClient)
        super().tearDown()

    def test_update_return_payment_state_exception(self):
        mock_error_response: CommercetoolsError = CommercetoolsError(
            "Could not update ReturnPaymentState", [
                {
                    "code": "ConcurrentModification",
                    "detailedErrorMessage": "Object [mock_order_id] has a "
                                            "different version than expected. Expected: 3 - Actual: 2."
                },
            ], {}, "123456"
        )

        def _throw(_payment_id):
            raise mock_error_response

        self.mock.payment_mock.side_effect = _throw

        with self.assertRaises(OpenEdxFilterException):
            self.client_set.client.update_return_payment_state_after_successful_refund(
                order_id="mock_order_id",
                order_version="2",
                return_line_item_return_ids=["mock_return_item_id"],
                return_line_entitlement_ids={'mock_return_item_id': 'mock_entitlement_id'},
                refunded_line_item_refunds={},
                payment_intent_id="1",
                interaction_id=uuid4_str()
            )

    def test_update_return_payment_state_no_payment(self):
        mock_error_response: CommercetoolsError = CommercetoolsError(
            "Could not update ReturnPaymentState", [
                {
                    "code": "ConcurrentModification",
                    "detailedErrorMessage": "Object [mock_order_id] has a "
                                            "different version than expected. Expected: 3 - Actual: 2."
                },
            ], {}, "123456"
        )

        def _throw(_payment_id):
            raise mock_error_response

        self.mock.payment_mock.side_effect = _throw

        with self.assertRaises(OpenEdxFilterException):
            self.client_set.client.update_return_payment_state_after_successful_refund(
                order_id="mock_order_id",
                order_version="2",
                return_line_item_return_ids=["mock_return_item_id"],
                return_line_entitlement_ids={'mock_return_item_id': 'mock_entitlement_id'},
                refunded_line_item_refunds={},
                payment_intent_id="1",
                interaction_id=uuid4_str()
            )

    def test_get_product_by_program_id(self):
        base_url = self.client_set.get_base_url_from_client()
        program_id = "mock_program_id"
        expected_product = {
            "id": "mock_product_id",
            "key": program_id,
            "name": {"en": "Mock Product"}
        }

        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.get(
                f"{base_url}product-projections/search?filter=key%3A%22{program_id}%22",
                json={"results": [expected_product], "total": 1}
            )

            result = self.client_set.client.get_product_by_program_id(program_id)
            self.assertIsNotNone(result)
            self.assertEqual(result.id, expected_product["id"])
            self.assertEqual(result.key, expected_product["key"])

    def test_get_product_by_program_id_not_found(self):
        base_url = self.client_set.get_base_url_from_client()
        program_id = "non_existent_program_id"

        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.get(
                f"{base_url}product-projections/search?filter=key%3A%22{program_id}%22",
                json={"results": [], "total": 0}
            )

            result = self.client_set.client.get_product_by_program_id(program_id)
            self.assertIsNone(result)
