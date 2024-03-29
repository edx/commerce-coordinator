"""
API clients for commercetools app.
"""

import logging
from typing import Generic, List, Optional, Tuple, TypeVar, Union

import requests
from commercetools import Client as CTClient
from commercetools import CommercetoolsError
from commercetools.platform.models import Customer as CTCustomer
from commercetools.platform.models import CustomerSetCustomTypeAction as CTCustomerSetCustomTypeAction
from commercetools.platform.models import FieldContainer as CTFieldContainer
from commercetools.platform.models import Order as CTOrder
from commercetools.platform.models import OrderAddReturnInfoAction, OrderSetReturnPaymentStateAction
from commercetools.platform.models import ProductVariant as CTProductVariant
from commercetools.platform.models import ReturnItemDraft, ReturnPaymentState, ReturnShipmentState
from commercetools.platform.models import Type as CTType
from commercetools.platform.models import TypeDraft as CTTypeDraft
from commercetools.platform.models import TypeResourceIdentifier as CTTypeResourceIdentifier
from django.conf import settings
from openedx_filters.exceptions import OpenEdxFilterException

from commerce_coordinator.apps.commercetools.catalog_info.constants import DEFAULT_ORDER_EXPANSION, EdXFieldNames
from commerce_coordinator.apps.commercetools.catalog_info.foundational_types import TwoUCustomTypes
from commerce_coordinator.apps.core.constants import ORDER_HISTORY_PER_SYSTEM_REQ_LIMIT

logger = logging.getLogger(__name__)

T = TypeVar("T")

ExpandList = Union[Tuple[str], List[str]]


class PaginatedResult(Generic[T]):
    """ Planned paginated response wrapper """
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

    def __getitem__(self, item):
        return getattr(self, item)

    def rebuild(self, results: List[T]):
        return PaginatedResult(results, total=self.total, offset=self.offset)


class CommercetoolsAPIClient:
    """ Commercetools API Client """
    base_client = None

    def __init__(self):
        """
        Initialize CommercetoolsAPIClient, for use in an application, or (with an arg) testing.

        Args:
             client(CTClient): A mock client for testing (ONLY).
        """
        super().__init__()

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
        """
        Ensures a custom type exists within CoCo
        Args:
            type_def: The type definition draft.

        Returns: The formal type with identifier or None

        """
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
        """
        Updates a CoCo Customer Object with what we are currently using for LMS Identifiers
        Args:
            customer: Customer Object from CoCo
            lms_user_id: edX LMS User ID #
            lms_user_name: edX LMS Username

        Returns: Updated CoCo customer object

        """
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

        if results.count == 0:
            return None
        else:
            return results.results[0]

    def get_order_by_id(self, order_id: str, expand: ExpandList = DEFAULT_ORDER_EXPANSION) -> CTOrder:
        """
        Fetch an order by the Order ID (UUID)

        Args:
            order_id (str): Order ID (UUID)
            expand: List of Order Parameters to expand

        Returns (CTOrder): Order with Expanded Properties
        """
        return self.base_client.orders.get_by_id(order_id, expand=list(expand))  # pragma no cover

    def get_orders(self, customer: CTCustomer, offset=0,
                   limit=ORDER_HISTORY_PER_SYSTEM_REQ_LIMIT,
                   expand: ExpandList = DEFAULT_ORDER_EXPANSION,
                   order_state="Complete") -> PaginatedResult[CTOrder]:

        """
        Call commercetools API overview endpoint for data about historical orders.

        Args:
            customer (CTCustomer): Commerce Tools Customer to look up orders for
            offset (int): Pagination Offset
            limit (int): Maximum number of results
            expand: List of Order Parameters to expand

        Returns:
            PaginatedResult[CTOrder]: Dictionary representation of JSON returned from API

        See sample response in tests.py

        """
        order_where_clause = f"orderState=\"{order_state}\""
        values = self.base_client.orders.query(
            where=["customerId=:cid", order_where_clause],
            predicate_var={'cid': customer.id},
            sort=["completedAt desc", "lastModifiedAt desc"],
            limit=limit,
            offset=offset,
            expand=list(expand)
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

        if customer is None:  # pragma: no cover
            raise ValueError(f'Unable to locate customer with ID #{edx_lms_user_id}')

        orders = self.get_orders(customer, offset, limit)

        return orders, customer

    def get_customer_by_id(self, customer_id: str) -> CTCustomer:
        return self.base_client.customers.get_by_id(customer_id)  # pragma no cover

    def get_product_variant_by_course_run(self, cr_id: str) -> Optional[CTProductVariant]:
        """
        Args:
            cr_id: variant course run key
        """
        results = self.base_client.product_projections.search(False, filter=f"variants.sku:\"{cr_id}\"").results

        if len(results) < 1:  # pragma no cover
            return None

        # Make 2D List of all variants from all results, and then flatten
        all_variants = [listitem for sublist in
                        list(
                            map(
                                lambda selection: [selection.master_variant, *selection.variants],
                                results
                            )
                        )
                        for listitem in sublist]

        matching_variant_list = list(
            filter(
                lambda v: v.sku == cr_id,
                all_variants
            )
        )

        if len(matching_variant_list) < 1:  # pragma no cover
            return None

        return matching_variant_list[0]

    def create_return_for_order(self, order_id: str, order_version: str, order_line_id: str) -> CTOrder:
        """
        Creates refund/return for Commercetools order
        Args:
            order_id (str): Order ID (UUID)
            order_version (str): Current version of order
            order_line_id (str): ID of order line item
        Returns (CTOrder): Updated order object or
        Returns Exception: Error if update was unsuccesful.
        """

        try:
            return_item_draft_comment = f'Creating return item for order {order_id} with ' \
                                        f'order line id {order_line_id}'

            return_item_draft = ReturnItemDraft(
                quantity=1,
                line_item_id=order_line_id,
                comment=return_item_draft_comment,
                shipment_state=ReturnShipmentState.RETURNED
            )

            add_return_info_action = OrderAddReturnInfoAction(
                items=[return_item_draft]
            )

            returned_order = self.base_client.orders.update_by_id(
                id=order_id,
                version=order_version,
                actions=[add_return_info_action]
            )
            return returned_order
        except CommercetoolsError as err:
            logger.error(f"[CommercetoolsError] Unable to create return for "
                         f"order {order_id} with error correlation id {err.correlation_id} "
                         f"and error/s: {err.errors}")
            raise err

    def update_return_payment_state_after_successful_refund(self, order_id: str,
                                                            order_version: str,
                                                            return_line_item_return_id: str) -> CTOrder:
        """
        Update paymentState on the LineItemReturnItem attached to the order.
        Updated by the Order ID (UUID)

        Args:
            order_id (str): Order ID (UUID)
            order_version (str): Current version of order
            return_item_id (str): LineItemReturnItem ID

        Returns (CTOrder): Updated order object or
        Returns Exception: Error if update was unsuccesful.
        """
        try:

            return_payment_state_action = OrderSetReturnPaymentStateAction(
                return_item_id=return_line_item_return_id,
                payment_state=ReturnPaymentState.REFUNDED
            )

            updated_order = self.base_client.orders.update_by_id(
                id=order_id,
                version=order_version,
                actions=[return_payment_state_action]
            )
            return updated_order
        except CommercetoolsError as err:
            logger.error(f"[CommercetoolsError] Unable to update ReturnPaymentState "
                         f"of order {order_id} with error correlation id {err.correlation_id} "
                         f"and error/s: {err.errors}")
            raise OpenEdxFilterException(str(err)) from err
