"""
API clients for commercetools app.
"""

import datetime
import logging
from types import SimpleNamespace
from typing import Generic, List, Optional, Tuple, TypedDict, TypeVar, Union

import requests
from commercetools import Client as CTClient
from commercetools import CommercetoolsError
from commercetools.platform.models import Customer as CTCustomer
from commercetools.platform.models import CustomerChangeEmailAction, CustomerSetCustomFieldAction
from commercetools.platform.models import CustomerSetCustomTypeAction as CTCustomerSetCustomTypeAction
from commercetools.platform.models import CustomerSetFirstNameAction, CustomerSetLastNameAction
from commercetools.platform.models import FieldContainer as CTFieldContainer
from commercetools.platform.models import LineItem as CTLineItem
from commercetools.platform.models import Money as CTMoney
from commercetools.platform.models import Order as CTOrder
from commercetools.platform.models import (
    OrderAddReturnInfoAction,
    OrderSetLineItemCustomFieldAction,
    OrderSetReturnItemCustomTypeAction,
    OrderSetReturnPaymentStateAction,
    OrderTransitionLineItemStateAction
)
from commercetools.platform.models import Payment as CTPayment
from commercetools.platform.models import PaymentAddTransactionAction, PaymentSetTransactionCustomTypeAction
from commercetools.platform.models import ProductVariant as CTProductVariant
from commercetools.platform.models import (
    ReturnItemDraft,
    ReturnPaymentState,
    ReturnShipmentState,
    StateResourceIdentifier,
    TransactionDraft,
    TransactionType
)
from commercetools.platform.models import Type as CTType
from commercetools.platform.models import TypeDraft as CTTypeDraft
from commercetools.platform.models import TypeResourceIdentifier as CTTypeResourceIdentifier
from commercetools.platform.models.state import State as CTLineItemState
from django.conf import settings
from openedx_filters.exceptions import OpenEdxFilterException

from commerce_coordinator.apps.commercetools.catalog_info.constants import (
    DEFAULT_ORDER_EXPANSION,
    EDX_PAYPAL_PAYMENT_INTERFACE_NAME,
    EDX_STRIPE_PAYMENT_INTERFACE_NAME,
    EdXFieldNames,
    TwoUKeys
)
from commerce_coordinator.apps.commercetools.catalog_info.foundational_types import TwoUCustomTypes
from commerce_coordinator.apps.commercetools.utils import (
    find_latest_refund,
    find_refund_transaction,
    handle_commercetools_error,
    translate_refund_status_to_transaction_status
)
from commerce_coordinator.apps.core.constants import ORDER_HISTORY_PER_SYSTEM_REQ_LIMIT

logger = logging.getLogger(__name__)

T = TypeVar("T")

ExpandList = Union[Tuple[str], List[str]]


class PaginatedResult(Generic[T]):
    """Planned paginated response wrapper"""

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


class Refund(TypedDict):
    """
    Refund object definition
    """

    id: str
    amount: Union[str, int]
    currency: str
    created: Union[str, int]
    status: str


class CommercetoolsAPIClient:
    """Commercetools API Client"""

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
            scope=config["scopes"].split(" "),
            url=config["apiUrl"],
            token_url=config["authUrl"],
            project_key=config["projectKey"],
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
            raise ValueError(
                "User already has a custom type, and its not the one were expecting, Refusing to update. "
                "(Updating will eradicate the values from the other type, as an object may only have one "
                "Custom Type)"
            )

        ret = self.base_client.customers.update_by_id(
            customer.id,
            customer.version,
            actions=[
                CTCustomerSetCustomTypeAction(
                    type=CTTypeResourceIdentifier(
                        key=TwoUCustomTypes.CUSTOMER_TYPE_DRAFT.key,
                    ),
                    fields=CTFieldContainer(
                        {
                            EdXFieldNames.LMS_USER_ID: f"{lms_user_id}",
                            EdXFieldNames.LMS_USER_NAME: lms_user_name,
                        }
                    ),
                ),
            ],
        )

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

        logger.info(f"[CommercetoolsAPIClient] - Attempting to get customer with LMS user id: {lms_user_id}")

        edx_lms_user_id_key = EdXFieldNames.LMS_USER_ID

        start_time = datetime.datetime.now()
        results = self.base_client.customers.query(
            where=f"custom(fields({edx_lms_user_id_key}=:id))",
            limit=2,
            predicate_var={"id": f"{lms_user_id}"},
        )
        duration = (datetime.datetime.now() - start_time).total_seconds()
        logger.info(f"[Performance Check] - customerId query took {duration} seconds")

        if results.count > 1:
            # We are unable due to CT Limitations to enforce unique LMS ID values on Customers on the catalog side, so
            #   let's do a backhanded check by trying to pull 2 users and erroring if we find a discrepancy.
            logger.info(
                f"[CommercetoolsAPIClient] - More than one customer found with LMS "
                f"user id: {lms_user_id}, raising error"
            )
            raise ValueError(
                "More than one user was returned from the catalog with this edX LMS User ID, these must be unique."
            )

        if results.count == 0:
            logger.info(f"[CommercetoolsAPIClient] - No customer found with LMS user id: {lms_user_id}")
            return None
        else:
            logger.info(f"[CommercetoolsAPIClient] - Customer found with LMS user id: {lms_user_id}")
            return results.results[0]

    def get_order_by_id(self, order_id: str, expand: ExpandList = DEFAULT_ORDER_EXPANSION) -> CTOrder:
        """
        Fetch an order by the Order ID (UUID)

        Args:
            order_id (str): Order ID (UUID)
            expand: List of Order Parameters to expand

        Returns (CTOrder): Order with Expanded Properties
        """
        logger.info(f"[CommercetoolsAPIClient] - Attempting to find order with id: {order_id}")
        return self.base_client.orders.get_by_id(order_id, expand=list(expand))

    def get_order_by_number(self, order_number: str, expand: ExpandList = DEFAULT_ORDER_EXPANSION) -> CTOrder:
        """
        Fetch an order by the Order Number (Human readable order number)

        Args:
            order_number (str): Order Number (Human readable order number)
            expand: List of Order Parameters to expand

        Returns (CTOrder): Order with Expanded Properties
        """
        logger.info(f"[CommercetoolsAPIClient] - Attempting to find order with number {order_number}")
        return self.base_client.orders.get_by_order_number(order_number, expand=list(expand))

    def get_orders(
        self,
        customer_id: str,
        offset=0,
        limit=ORDER_HISTORY_PER_SYSTEM_REQ_LIMIT,
        expand: ExpandList = DEFAULT_ORDER_EXPANSION,
        order_state="Complete",
    ) -> PaginatedResult[CTOrder]:
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
        logger.info(
            f"[CommercetoolsAPIClient] - Attempting to find all completed orders for " f"customer with ID {customer_id}"
        )
        order_where_clause = f'orderState="{order_state}"'

        start_time = datetime.datetime.now()
        values = self.base_client.orders.query(
            where=["customerId=:cid", order_where_clause],
            predicate_var={"cid": customer_id},
            sort=["completedAt desc", "lastModifiedAt desc"],
            limit=limit,
            offset=offset,
            expand=list(expand),
        )
        duration = (datetime.datetime.now() - start_time).total_seconds()
        logger.info(f"[Performance Check] get_orders call took {duration} seconds")

        return PaginatedResult(values.results, values.total, values.offset)

    def get_orders_for_customer(
        self,
        edx_lms_user_id: int,
        offset=0,
        limit=ORDER_HISTORY_PER_SYSTEM_REQ_LIMIT,
        customer_id=None,
        email=None,
        username=None,
    ) -> (PaginatedResult[CTOrder], CTCustomer):
        """

        Args:
            edx_lms_user_id (object):
            offset:
            limit:
        """
        if not customer_id:
            customer = self.get_customer_by_lms_user_id(edx_lms_user_id)

            if customer is None:  # pragma: no cover
                raise ValueError(f"Unable to locate customer with ID #{edx_lms_user_id}")

            customer_id = customer.id
        else:
            if email is None or username is None:  # pragma: no cover
                raise ValueError("If customer_id is provided, both email and username must be provided")

            customer = SimpleNamespace(
                id=customer_id,
                email=email,
                custom=SimpleNamespace(fields={EdXFieldNames.LMS_USER_NAME: username}),
            )

        orders = self.get_orders(customer_id, offset, limit)

        return orders, customer

    def get_customer_by_id(self, customer_id: str) -> CTCustomer:
        logger.info(f"[CommercetoolsAPIClient] - Attempting to find customer with ID {customer_id}")
        return self.base_client.customers.get_by_id(customer_id)

    def get_state_by_id(self, state_id: str) -> CTLineItemState:
        logger.info(f"[CommercetoolsAPIClient] - Attempting to find state with id {state_id}")
        return self.base_client.states.get_by_id(state_id)

    def get_state_by_key(self, state_key: str) -> CTLineItemState:
        logger.info(f"[CommercetoolsAPIClient] - Attempting to find state with key {state_key}")
        return self.base_client.states.get_by_key(state_key)

    def get_payment_by_key(self, payment_key: str) -> CTPayment:
        logger.info(f"[CommercetoolsAPIClient] - Attempting to find payment with key {payment_key}")
        return self.base_client.payments.get_by_key(payment_key)

    def get_payment_by_transaction_interaction_id(self, interaction_id: str) -> CTPayment:
        """
        Fetch a payment by the transaction interaction ID
        """
        logger.info(f"[CommercetoolsAPIClient] - Attempting to find payment with interaction ID {interaction_id}")
        return self.base_client.payments.query(where=f'transactions(interactionId="{interaction_id}")').results[0]

    def get_product_by_program_id(self, program_id: str) -> Optional[CTProductVariant]:
        """
        Fetches a program product from Commercetools.
        Args:
            program_id: The ID of the program (bundle) to fetch.
        Returns:
            CTProductVariant if found, None otherwise.
        """
        results = self.base_client.product_projections.search(False, filter=f'key:"{program_id}"').results

        return results[0] if results else None

    def get_product_variant_by_course_run(self, cr_id: str) -> Optional[CTProductVariant]:
        """
        Args:
            cr_id: variant course run key
        """
        start_time = datetime.datetime.now()
        results = self.base_client.product_projections.search(False, filter=f'variants.sku:"{cr_id}"').results
        duration = (datetime.datetime.now() - start_time).total_seconds()
        logger.info(f"[Performance Check] get_product_variant_by_course_run took {duration} seconds")

        if len(results) < 1:  # pragma no cover
            return None

        # Make 2D List of all variants from all results, and then flatten
        all_variants = [
            listitem
            for sublist in list(
                map(
                    lambda selection: [selection.master_variant, *selection.variants],
                    results,
                )
            )
            for listitem in sublist
        ]

        matching_variant_list = list(filter(lambda v: v.sku == cr_id, all_variants))

        if len(matching_variant_list) < 1:  # pragma no cover
            return None

        return matching_variant_list[0]

    def create_return_for_order(self, order_id: str, order_version: int, order_line_item_id: str) -> CTOrder:
        """
        Creates refund/return for Commercetools order
        Args:
            order_id (str): Order ID (UUID)
            order_version (int): Current version of order
            order_line_item_id (str): ID of order line item
        Returns (CTOrder): Updated order object or
        Returns Exception: Error if update was unsuccessful.
        """

        try:
            return_item_draft_comment = (
                f"Creating return item for order {order_id} with " f"order line item ID {order_line_item_id}"
            )

            logger.info(f"[CommercetoolsAPIClient] - {return_item_draft_comment}")

            return_item_draft = ReturnItemDraft(
                quantity=1,
                line_item_id=order_line_item_id,
                comment=return_item_draft_comment,
                shipment_state=ReturnShipmentState.RETURNED,
            )

            add_return_info_action = OrderAddReturnInfoAction(items=[return_item_draft])

            returned_order = self.base_client.orders.update_by_id(
                id=order_id, version=order_version, actions=[add_return_info_action]
            )
            return returned_order
        except CommercetoolsError as err:
            handle_commercetools_error("[CommercetoolsAPIClient.create_return_for_order]",
                                       err, f"Unable to create return for order {order_id}")
            raise err

    def update_return_payment_state_for_enrollment_code_purchase(
        self,
        order_id: str,
        order_version: int,
        return_line_item_return_ids: List[str],
    ) -> Union[CTOrder, None]:
        """
        Update paymentState on the LineItemReturnItem attached to the order for enrollment code purchase.
        Updated by the Order ID (UUID)

        Args:
            order_id (str): Order ID (UUID)
            order_version (int): Current version of order
            return_line_item_return_id (str): LineItemReturnItem ID

        Returns (CTOrder): Updated order object or
        Raises Exception: Error if update was unsuccessful.
        """

        try:
            logger.info(
                f"[CommercetoolsAPIClient."
                "update_return_payment_state_for_enrollment_code_purchase] - "
                "Updating payment state for return "
                f"with ids {return_line_item_return_ids} to '{ReturnPaymentState.NOT_REFUNDED}'."
            )
            return_payment_state_actions = []
            for return_line_item_return_id in return_line_item_return_ids:
                return_payment_state_actions.append(OrderSetReturnPaymentStateAction(
                    return_item_id=return_line_item_return_id,
                    payment_state=ReturnPaymentState.NOT_REFUNDED,
                ))

            updated_order = self.base_client.orders.update_by_id(
                id=order_id,
                version=order_version,
                actions=return_payment_state_actions,
            )
            logger.info(f"Successfully updated return payment state to not refunded "
                        f"for enrollment code purchase - order_id: {order_id}")
            return updated_order
        except CommercetoolsError as err:
            handle_commercetools_error(
                "[CommercetoolsAPIClient."
                "update_return_payment_state_for_enrollment_code_purchase]",
                err, f"Unable to update ReturnPaymentState of order {order_id}"
            )
            raise err

    def update_return_payment_state_after_successful_refund(
        self,
        order_id: str,
        order_version: int,
        return_line_item_return_ids: List[str],
        return_line_entitlement_ids: dict,
        refunded_line_item_refunds: dict,
        payment_intent_id: str,
        interaction_id: str
    ) -> Union[CTOrder, None]:
        """
        Update paymentState on the LineItemReturnItem attached to the order.
        Updated by the Order ID (UUID)

        Args:
            order_id (str): Order ID (UUID)
            order_version (int): Current version of order
            return_line_item_return_id (str): LineItemReturnItem ID

        Returns (CTOrder): Updated order object or
        Raises Exception: Error if update was unsuccessful.
        """
        try:
            logger.info(
                f"[CommercetoolsAPIClient] - Updating payment state for return "
                f"with ids {return_line_item_return_ids} to '{ReturnPaymentState.REFUNDED}'."
            )
            if not payment_intent_id:
                payment_intent_id = ""
            logger.info(f"Updating return for order: {order_id} - payment_intent_id: {payment_intent_id}")
            payment = self.get_payment_by_key(payment_intent_id)
            logger.info(f"Payment found: {payment}")
            transaction_id = find_refund_transaction(payment, interaction_id)

            # Handles the case when refund is created from PSP and interaction ID is not set. In that case
            # transaction ID will also be.
            if not transaction_id:
                transaction_id = find_latest_refund(payment)

            return_payment_state_actions = []
            update_transaction_id_actions = []
            for return_line_item_return_id in return_line_item_return_ids:
                return_payment_state_actions.append(OrderSetReturnPaymentStateAction(
                    return_item_id=return_line_item_return_id,
                    payment_state=ReturnPaymentState.REFUNDED,
                ))
                custom_fields = {
                    "transactionId": refunded_line_item_refunds.get(return_line_item_return_id, transaction_id),
                }
                entitlement_id = return_line_entitlement_ids.get(return_line_item_return_id)
                if entitlement_id:
                    custom_fields[TwoUKeys.LINE_ITEM_LMS_ENTITLEMENT_ID] = entitlement_id
                update_transaction_id_actions.append(OrderSetReturnItemCustomTypeAction(
                    return_item_id=return_line_item_return_id,
                    type=CTTypeResourceIdentifier(
                        key="returnItemCustomType",
                    ),
                    fields=CTFieldContainer(custom_fields),
                ))

            logger.info(f"Update return payment state after successful refund - payment_intent_id: {payment_intent_id}")

            updated_order = self.base_client.orders.update_by_id(
                id=order_id,
                version=order_version,
                actions=return_payment_state_actions + update_transaction_id_actions,
            )
            if transaction_id:
                return_transaction_return_item_action = PaymentSetTransactionCustomTypeAction(
                    transaction_id=transaction_id,
                    type=CTTypeResourceIdentifier(key="transactionCustomType"),
                    fields=CTFieldContainer({"returnItemId": ', '.join(return_line_item_return_ids)}),
                )
                self.base_client.payments.update_by_id(
                    id=payment.id,
                    version=payment.version,
                    actions=[return_transaction_return_item_action],
                )
            logger.info("Updated transaction with return item id")
            return updated_order
        except CommercetoolsError as err:
            handle_commercetools_error("[CommercetoolsAPIClient.update_return_payment_state_after_successful_refund]",
                                       err, f"Unable to update ReturnPaymentState of order {order_id}")
            raise OpenEdxFilterException(str(err)) from err

    def _preprocess_refund_object(self, refund: Refund, psp: str) -> Refund:
        """
        Pre process refund object based on PSP
        """
        if psp == EDX_PAYPAL_PAYMENT_INTERFACE_NAME:
            # Paypal sends amount in dollars and CT expects it in cents
            refund["amount"] = float(refund["amount"]) * 100
            refund["created"] = datetime.datetime.fromisoformat(refund["created"])
        else:
            refund["created"] = datetime.datetime.utcfromtimestamp(refund["created"])

        refund["status"] = translate_refund_status_to_transaction_status(refund["status"])
        refund["currency"] = refund["currency"].upper()
        return refund

    def create_return_payment_transaction(
        self, payment_id: str, payment_version: int, refund: Refund, psp=EDX_STRIPE_PAYMENT_INTERFACE_NAME
    ) -> CTPayment:
        """
        Create Commercetools payment transaction for refund
        Args:
            payment_id (str): Payment ID (UUID)
            payment_version (int): Current version of payment
            refund (Refund): Refund object
        Returns (CTPayment): Updated payment object or
        Raises Exception: Error if creation was unsuccessful.
        """
        try:
            logger.info(
                f"[CommercetoolsAPIClient] - Creating refund transaction for payment with ID {payment_id} "
                f"following successful refund {refund.get('id')} in PSP: {psp}"
            )
            refund = self._preprocess_refund_object(refund, psp)

            amount_as_money = CTMoney(
                cent_amount=int(refund["amount"]),
                currency_code=refund["currency"],
            )

            transaction_draft = TransactionDraft(
                type=TransactionType.REFUND,
                amount=amount_as_money,
                timestamp=refund["created"],
                state=refund["status"],
                interaction_id=refund["id"],
            )

            add_transaction_action = PaymentAddTransactionAction(transaction=transaction_draft)

            returned_payment = self.base_client.payments.update_by_id(
                id=payment_id, version=payment_version, actions=[add_transaction_action]
            )

            return returned_payment
        except CommercetoolsError as err:
            context = (
                f"Unable to create refund payment transaction for payment {payment_id}, refund {refund['id']} "
                f"with PSP: {psp}"
            )
            handle_commercetools_error("[CommercetoolsAPIClient.create_return_payment_transaction]", err, context)
            raise err

    def update_line_item_on_fulfillment(
        self,
        entitlement_uuid: str,
        order_id: str,
        order_version: int,
        line_item_id: str,
        item_quantity: int,
        from_state_id: str,
        new_state_key: str,
    ) -> CTOrder:
        """
        Update Commercetools order line item on fulfillment.
        Args:
            entitlement_uuid (str): Entitlement UUID
            order_id (str): Order ID (UUID)
            order_version (int): Current version of order
            line_item_id (str): ID of order line item
            item_quantity (int): Count of variants in line item
            from_state_id (str): ID of LineItemState to transition from
            new_state_key (str): Key of LineItemState to transition to
        Returns (CTOrder): Updated order object or
        Returns (CTOrder): Current un-updated order
        Raises Exception: Error if update was unsuccessful.
        """
        from_state_key = self.get_state_by_id(from_state_id).key

        logger.info(
            f"[CommercetoolsAPIClient] - Transitioning line item state for order with ID {order_id} "
            f"from {from_state_key} to {new_state_key}"
        )

        try:
            actions = []
            if entitlement_uuid:
                logger.info(
                    f"[CommercetoolsAPIClient] - Adding entitlement_uuid for order with ID {order_id} "
                )
                actions.append(OrderSetLineItemCustomFieldAction(
                    line_item_id=line_item_id,
                    name=TwoUKeys.LINE_ITEM_LMS_ENTITLEMENT_ID,
                    value=entitlement_uuid,
                ))
            if new_state_key != from_state_key:
                actions.append(OrderTransitionLineItemStateAction(
                    line_item_id=line_item_id,
                    quantity=item_quantity,
                    from_state=StateResourceIdentifier(key=from_state_key),
                    to_state=StateResourceIdentifier(key=new_state_key),
                ))

            if actions:
                return self.base_client.orders.update_by_id(
                    id=order_id,
                    version=order_version,
                    actions=actions,
                )
            else:
                logger.info(
                    f"[CommercetoolsAPIClient] - The line item {line_item_id} "
                    f"already has the correct state {new_state_key}. "
                    f"Not attempting to transition LineItemState for order id {order_id}"
                )
                return self.get_order_by_id(order_id)

        except CommercetoolsError as err:
            context_prefix = "[CommercetoolsAPIClient.update_line_item_on_fulfillment]"
            # Logs & ignores version conflict errors due to duplicate Commercetools messages
            handle_commercetools_error(
                context_prefix, err,
                f"Failed to update LineItem of order {order_id}"
                f"From State: '{from_state_key}' "
                f"To State: '{new_state_key}' "
                f"And entitlement {entitlement_uuid} "
                f"Line Item ID: {line_item_id}"
            )
            raise err

    def update_line_items_transition_state(
            self,
            order_id: str,
            order_version: int,
            line_items: List[CTLineItem],
            from_state_id: str,
            new_state_key: str,
    ) -> CTOrder:
        """
        Update Commercetools order line item state for all items in one call.
        Args:
            order_id (str): Order ID (UUID)
            order_version (int): Current version of order
            line_items (List[object]): List of line item objects
            from_state_id (str): ID of LineItemState to transition from
            new_state_key (str): Key of LineItemState to transition to
        Returns (CTOrder): Updated order object or
        Returns (CTOrder): Current un-updated order
        Raises Exception: Error if update was unsuccessful.
        """

        from_state_key = self.get_state_by_id(from_state_id).key

        logger.info(
            f"[CommercetoolsAPIClient] - Transitioning line item states for order ID '{order_id}'. "
            f"From State: '{from_state_key}' "
            f"To State: '{new_state_key}' "
            f"Line Item IDs: {', '.join(item.id for item in line_items)}"
        )

        try:
            if new_state_key != from_state_key:
                actions = [
                    OrderTransitionLineItemStateAction(
                        line_item_id=item.id,
                        quantity=item.quantity,
                        from_state=StateResourceIdentifier(key=from_state_key),
                        to_state=StateResourceIdentifier(key=new_state_key),
                    )
                    for item in line_items
                ]

                return self.base_client.orders.update_by_id(
                    id=order_id,
                    version=order_version,
                    actions=actions,
                )
            else:
                logger.info(
                    f"All line items already have the correct state {new_state_key}. "
                    "Not attempting to transition LineItemState"
                )
                return self.get_order_by_id(order_id)
        except CommercetoolsError as err:
            # Logs & ignores version conflict errors due to duplicate Commercetools messages
            handle_commercetools_error(
                "[CommercetoolsAPIClient.update_line_items_transition_state]",
                err,
                f"Failed to update LineItemStates for order ID '{order_id}'. "
                f"From State: '{from_state_key}' "
                f"To State: '{new_state_key}' "
                f"Line Item IDs: {', '.join(item.id for item in line_items)}",
                True
            )
            raise err

    def retire_customer_anonymize_fields(
        self,
        customer_id: str,
        customer_version: int,
        retired_first_name: str,
        retired_last_name: str,
        retired_email: str,
        retired_lms_username: str,
    ) -> CTCustomer:
        """
        Update Commercetools customer with anonymized fields
        Args:
            customer_id (str): Customer ID (UUID)
            customer_version (int): Current version of customer
            retired_first_name (str): anonymized customer first name value
            retired_last_name (str): anonymized customer last name value
            retired_email (str): anonymized customer email value
            retired_lms_username (str): anonymized customer lms username value
        Returns (CTCustomer): Updated customer object or
        Raises Exception: Error if update was unsuccessful.
        """

        actions = []
        update_retired_first_name_action = CustomerSetFirstNameAction(first_name=retired_first_name)

        update_retired_last_name_action = CustomerSetLastNameAction(last_name=retired_last_name)

        update_retired_email_action = CustomerChangeEmailAction(email=retired_email)

        update_retired_lms_username_action = CustomerSetCustomFieldAction(
            name="edx-lms_user_name", value=retired_lms_username
        )

        actions.extend(
            [
                update_retired_first_name_action,
                update_retired_last_name_action,
                update_retired_email_action,
                update_retired_lms_username_action,
            ]
        )

        try:
            retired_customer = self.base_client.customers.update_by_id(
                id=customer_id, version=customer_version, actions=actions
            )
            return retired_customer
        except CommercetoolsError as err:
            logger.error(
                f"[CommercetoolsError] Unable to anonymize customer fields for customer "
                f"with ID: {customer_id}, after LMS retirement with "
                f"error correlation id {err.correlation_id} and error/s: {err.errors}"
            )
            raise err

    def is_first_time_discount_eligible(self, email: str, code: str) -> bool:
        """
        Check if a user is eligible for a first time discount
        Args:
            email (str): Email of the user
            code (str): First time discount code
        Returns (bool): True if the user is eligible for a first time discount
        """
        try:
            discounted_orders = self.base_client.orders.query(
                where=[
                    "customerEmail=:email",
                    "orderState=:orderState",
                    "discountCodes(discountCode is defined)"
                ],
                predicate_var={'email': email, 'orderState': 'Complete'},
                expand=["discountCodes[*].discountCode"]
            )

            if discounted_orders.total < 1:
                return True

            discounted_orders = discounted_orders.results

            for order in discounted_orders:
                discount_code = order.discount_codes[0].discount_code.obj.code
                if discount_code == code:
                    return False

            return True
        except CommercetoolsError as err:  # pragma no cover
            # Logs & ignores version conflict errors due to duplicate Commercetools messages
            handle_commercetools_error("[CommercetoolsAPIClient.is_first_time_discount_eligible]",
                                       err, f"Unable to check if user {email} is eligible for a "
                                            f"first time discount", True)
            return True
