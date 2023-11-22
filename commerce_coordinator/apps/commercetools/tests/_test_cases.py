""" Fallback Monkeypatched Test Case """

from typing import List
from unittest import TestCase

from commercetools.platform.models import Customer as CTCustomer
from commercetools.platform.models import Order as CTOrder

from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient, PaginatedResult
from commerce_coordinator.apps.commercetools.tests.conftest import MonkeyPatch, gen_order
from commerce_coordinator.apps.commercetools.tests.test_data import gen_customer
from commerce_coordinator.apps.core.constants import ORDER_HISTORY_PER_SYSTEM_REQ_LIMIT
from commerce_coordinator.apps.core.tests.utils import uuid4_str


class MonkeyPatchedGetOrderTestCase(TestCase):
    """A test case with the CT API Client Patched"""
    orders: List[CTOrder] = {}

    def setupOrders(self):
        self.orders = [gen_order(uuid4_str())]

    def setUp(self):
        super().setUp()
        self.setupOrders()
        MonkeyPatch.monkey(
            CommercetoolsAPIClient,
            {
                '__init__': lambda _: None,
                'get_orders_for_customer': self.get_orders_for_customer()
            }
        )

    def tearDown(self):
        super().tearDown()
        if MonkeyPatch.is_monkey(CommercetoolsAPIClient):
            MonkeyPatch.unmonkey(CommercetoolsAPIClient)

    def get_orders_for_customer(self):
        """Indirect function call for mocked orders in Monkeypatched client"""
        # noinspection PyUnusedLocal
        # pylint: disable=unused-argument # needed for kwargs
        def _get_orders_for_customer(
            _, edx_lms_user_id: int, offset=0,
                limit=ORDER_HISTORY_PER_SYSTEM_REQ_LIMIT
        ) -> (PaginatedResult[CTOrder], CTCustomer):
            return (
                PaginatedResult(self.orders, len(self.orders), offset),
                gen_customer(email="hiya@email.test", un="dave")
            )
        # pylint: enable=unused-argument # needed for kwargs

        return _get_orders_for_customer
