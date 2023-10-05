"""
API clients for commercetools app.
"""

import logging
from typing import Generic, List, Optional, TypeVar

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

    def __init__(self):
        super().__init__()
        config = settings.COMMERCETOOLS_CONFIG
        self.base_client = CTClient(
            client_id=config["clientId"],
            client_secret=config["clientSecret"],
            scope=[config["scopes"]],
            url=config["apiUrl"],
            token_url=config["authUrl"],
            project_key=config["projectKey"]
        )

    def ensure_custom_type_exists(self, type_def: CTTypeDraft) -> CTType:
        type_object = None
        type_exists = False
        try:
            type_object = self.base_client.types.get_by_key(type_def.key)
            type_exists = True
        except CommercetoolsError as _:
            # commercetools.exceptions.CommercetoolsError: The Resource with key 'edx-user_information' was not found.
            pass

        if not type_exists:
            type_object = self.base_client.types.create(type_def)

        return type_object

    def tag_customer_with_lms_user_ud(self, customer: CTCustomer, lms_user_id: int) -> CTCustomer:

        # All updates to CT Core require the version of the object you are working on as protection from out of band
        #   updates, this does mean we have to fetch every (primary) object we want to chain.

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
                fields=CTFieldContainer({EdXFieldNames.LMS_USER_ID: lms_user_id})
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

        # NOTE: I have a question to CT of if we can use parameter binding here. (Row 41)
        results = self.base_client.customers.query(
            where=f'custom(fields({edx_lms_user_id_key}={lms_user_id}))',
            limit=2
        )

        if results.count > 1:
            # We are unable due to CT Limitations to enforce this on the catalog side, so lets do a backhanded check
            #   by trying to pull 2 users and erroring if we find a discrepancy.
            raise ValueError("More than one user was returned from the catalog with this edX LMS User ID, these must "
                             "be unique.")
        elif results.count == 0:
            return None
        else:
            return results.results[0]

    def get_orders(self, edx_lms_user_id: int, offset=0, limit=10) -> PaginatedResult[CTOrder]:
        """
        Call commercetools API overview endpoint for data about an order.

        Keyword Args:
            edx_lms_user_id: restrict to orders by this username

        Returns:
            PaginatedResult[CTOrder]: Dictionary representation of JSON returned from API

        See sample response in tests.py

        """
        customer = self.get_customer_by_lms_user_id(edx_lms_user_id)

        if customer is None:
            raise ValueError(f'Unable to locate customer with ID #{edx_lms_user_id}')

        values = self.base_client.orders.query(
            where="customerId=:cid",
            predicate_var={'cid': customer.id},
            sort="completedAt desc",
            limit=limit,
            offset=offset
        )

        return PaginatedResult(values.results, values.total, values.offset)
