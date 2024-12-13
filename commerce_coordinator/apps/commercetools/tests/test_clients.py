""" Commercetools API Client(s) Testing """

import pytest
import requests_mock
import stripe
from commercetools import CommercetoolsError
from commercetools.platform.models import (
    Customer,
    CustomerDraft,
    CustomerPagedQueryResponse,
    MoneyType,
    Order,
    OrderPagedQueryResponse,
    ReturnInfo,
    ReturnPaymentState,
    ReturnShipmentState,
    TransactionState,
    TransactionType,
    Type,
    TypedMoney,
    TypeDraft
)
from django.test import TestCase
from mock import patch
from openedx_filters.exceptions import OpenEdxFilterException

from commerce_coordinator.apps.commercetools.catalog_info.constants import EdXFieldNames, TwoUKeys
from commerce_coordinator.apps.commercetools.catalog_info.foundational_types import TwoUCustomTypes
from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient, PaginatedResult
from commerce_coordinator.apps.commercetools.tests.conftest import (
    APITestingSet,
    MonkeyPatch,
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
                    f"[CommercetoolsError] Unable to create return for "
                    f"order mock_order_id "
                    f"- Correlation ID: {exception.correlation_id}, Details: {exception.errors}"
                )

                log_mock.assert_called_once_with(expected_message)

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
                                                              TypedMoney(cent_amount=4900,
                                                                         currency_code='USD',
                                                                         type=MoneyType.CENT_PRECISION,
                                                                         fraction_digits=2))
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
                mock_response_return_item.line_item_id,
                mock_payment.id,
                10000
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
                    f"[CommercetoolsError] Unable to create refund payment transaction for "
                    f"payment mock_payment_id and refund {mock_stripe_refund.id} "
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

            result = self.client_set.client.update_line_item_transition_state_on_fulfillment(
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

            with patch('commerce_coordinator.apps.commercetools.clients.logging.Logger.info') as log_mock:
                self.client_set.client.update_line_item_transition_state_on_fulfillment(
                    "mock_order_id",
                    1,
                    "mock_order_line_item_id",
                    1,
                    "mock_order_line_item_state.id",
                    TwoUKeys.SUCCESS_FULFILMENT_STATE
                )

                expected_message = (
                    f"[CommercetoolsError] Unable to update LineItemState "
                    f"of order mock_order_id "
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
            result = self.client_set.client.update_line_item_transition_state_on_fulfillment(
                mock_order.id,
                mock_order.version,
                line_item_id,
                1,
                mock_order.line_items[0].state[0].state.id,
                TwoUKeys.PROCESSING_FULFILMENT_STATE
            )

            expected_message = (
                f"The line item {line_item_id} already has the correct state {mock_line_item_state.key}. "
                f"Not attempting to transition LineItemState"
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
                return_line_item_return_id="mock_return_item_id",
                payment_intent_id="1",
                amount_in_cents=10000
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
                return_line_item_return_id="mock_return_item_id",
                payment_intent_id=None,
                amount_in_cents=10000
            )
