"""
API clients for commercetools app.
"""

import logging
import typing
from typing import Generic, List, Optional, TypeVar

import requests
from commercetools import Client as CTClient
from commercetools import CommercetoolsError
from commercetools.platform.models import Customer as CTCustomer
from commercetools.platform.models import CustomerSetCustomTypeAction as CTCustomerSetCustomTypeAction
from commercetools.platform.models import FieldContainer as CTFieldContainer
from commercetools.platform.models import Order as CTOrder
from commercetools.platform.models import Type as CTType
from commercetools.platform.models import TypeDraft as CTTypeDraft
from commercetools.platform.models import TypeResourceIdentifier as CTTypeResourceIdentifier
from django.conf import settings

from commerce_coordinator.apps.commercetools.catalog_info.constants import EdXFieldNames
from commerce_coordinator.apps.commercetools.catalog_info.foundational_types import TwoUCustomTypes
from commerce_coordinator.apps.core import is_under_test
from commerce_coordinator.apps.core.constants import ORDER_HISTORY_PER_SYSTEM_REQ_LIMIT

logger = logging.getLogger(__name__)

T = TypeVar("T")


class PaginatedResult(Generic[T]):
    results: List[T]
    total: int
    offset: int

    def __init__(self, results: List[T], total: int, offset: int) -> None:
        super().__init__()
        self.results = results
        self.total = total
        self.offset = offset

    def next_offset(self) -> int:
        return self.offset + len(self.results)

    def has_more(self) -> bool:
        return (self.next_offset()) < self.total


class CommercetoolsAPIClient:  # (BaseEdxOAuthClient): ???
    base_client = None

    def __init__(self, client: typing.Optional[CTClient] = None):
        """
        Initialize CommercetoolsAPIClient, for use in an application, or (with an arg) testing.

        Args:
             client(CTClient): A mock client for testing (ONLY).
        """
        super().__init__()

        if client and not is_under_test():  # pragma: no cover
            # guard client
            raise RuntimeError('You must be invoking this through a test runner to supply a client.')
        elif client:  # we're under test so let's accept it
            self.base_client = client
        else:  # were not testing, let's build our own
            config = settings.COMMERCETOOLS_CONFIG
            self.base_client = CTClient(
                client_id=config["clientId"],
                client_secret=config["clientSecret"],
                scope=config["scopes"].split(' '),
                url=config["apiUrl"],
                token_url=config["authUrl"],
                project_key=config["projectKey"]
            )

    def ensure_custom_type_exists(self, type_def: CTTypeDraft) -> Optional[CTType]:
        type_object = None
        type_exists = False
        try:
            type_object = self.base_client.types.get_by_key(type_def.key)
            type_exists = True
        except CommercetoolsError as _:  # pragma: no cover
            # commercetools.exceptions.CommercetoolsError: The Resource with key 'edx-user_information' was not found.
            pass
        except requests.exceptions.HTTPError as _:  # The test framework doesn't wrap to CommercetoolsError
            pass

        if not type_exists:
            type_object = self.base_client.types.create(type_def)

        return type_object

    def tag_customer_with_lms_user_info(self, customer: CTCustomer, lms_user_id: int, lms_user_name: str) -> CTCustomer:

        # All updates to CT Core require the version of the object you are working on as protection from out of band
        #   updates; this does mean we have to fetch every (primary) object we want to chain.

        type_object = self.ensure_custom_type_exists(TwoUCustomTypes.CUSTOMER_TYPE_DRAFT)

        # A customer can only have one custom type associated to it, and thus only one set of custom fields. THUS...
        #   They can't be required, and shouldn't entirely be relied upon; Once a proper Type is changed, the old values
        #   are LOST.

        if customer.custom and not customer.custom.type.id == type_object.id:
            raise ValueError("User already has a custom type, and its not the one were expecting, Refusing to update. "
                             "(Updating will eradicate the values from the other type, as an object may only have one "
                             "Custom Type)")

        ret = self.base_client.customers.update_by_id(customer.id, customer.version, actions=[
            CTCustomerSetCustomTypeAction(
                type=CTTypeResourceIdentifier(
                    key=TwoUCustomTypes.CUSTOMER_TYPE_DRAFT.key,
                ),
                fields=CTFieldContainer({
                    EdXFieldNames.LMS_USER_ID: f"{lms_user_id}",
                    EdXFieldNames.LMS_USER_NAME: lms_user_name
                })
            ),
        ])

        return ret

    def get_customer_by_lms_user_id(self, lms_user_id: int) -> Optional[CTCustomer]:
        """
        Get a Commercetools Customer by their LMS User ID

        Args:
            lms_user_id: edX LMS User ID

        Returns:
            Optional[CTCustomer], A Commercetools Customer Object, or None if not found, may throw if more than one user
             is returned.
        """

        edx_lms_user_id_key = EdXFieldNames.LMS_USER_ID

        results = self.base_client.customers.query(
            where=f'custom(fields({edx_lms_user_id_key}=:id))',
            limit=2,
            predicate_var={'id': f"{lms_user_id}"}
        )

        if results.count > 1:
            # We are unable due to CT Limitations to enforce unique LMS ID values on Customers on the catalog side, so
            #   let's do a backhanded check by trying to pull 2 users and erroring if we find a discrepancy.
            raise ValueError("More than one user was returned from the catalog with this edX LMS User ID, these must "
                             "be unique.")
        elif results.count == 0:
            return None
        else:
            return results.results[0]

    def get_orders(self, customer: CTCustomer, offset=0,
                   limit=ORDER_HISTORY_PER_SYSTEM_REQ_LIMIT) -> PaginatedResult[CTOrder]:

        """
        Call commercetools API overview endpoint for data about historical orders.

        Args:
            customer (CTCustomer): Commerce Tools Customer to look up orders for
            offset (int): Pagination Offset
            limit (int): Maximum number of results

        Returns:
            PaginatedResult[CTOrder]: Dictionary representation of JSON returned from API

        See sample response in tests.py

        """
        values = self.base_client.orders.query(
            where="customerId=:cid",
            predicate_var={'cid': customer.id},
            sort=["completedAt desc", "lastModifiedAt desc"],
            limit=limit,
            offset=offset,
            expand=[
                "paymentInfo.payments[*]",
                "discountCodes[*].discountCode",
                "directDiscounts[*]"
            ]
        )

        return PaginatedResult(values.results, values.total, values.offset)

    def get_orders_for_customer(self, edx_lms_user_id: int, offset=0,
                                limit=ORDER_HISTORY_PER_SYSTEM_REQ_LIMIT) -> (PaginatedResult[CTOrder], CTCustomer):
        """

        Args:
            edx_lms_user_id (object):
            offset:
            limit:
        """
        customer = self.get_customer_by_lms_user_id(edx_lms_user_id)

        if customer is None:
            raise ValueError(f'Unable to locate customer with ID #{edx_lms_user_id}')

        orders = self.get_orders(customer, offset, limit)

        return orders, customer
