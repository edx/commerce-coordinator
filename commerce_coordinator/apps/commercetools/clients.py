"""
API clients for commercetools app.
"""

import datetime
import logging
from types import SimpleNamespace
from typing import Generic, List, Optional, Tuple, TypedDict, TypeVar, Union
import uuid

import requests
from commercetools import Client, CommercetoolsError
from commercetools.platform.models import (
    AuthenticationMode,
    BaseAddress,
    Cart,
    CartAddLineItemAction,
    CartAddPaymentAction,
    CartDraft,
    CartSetBillingAddressAction,
    CartSetCustomFieldAction,
    CartSetShippingAddressAction,
    Customer,
    CustomerChangeEmailAction,
    CustomerDraft,
    CustomerResourceIdentifier,
    CustomerSetCustomFieldAction,
    CustomerSetCustomTypeAction,
    CustomerSetFirstNameAction,
    CustomerSetLastNameAction,
    CustomFieldsDraft,
    CustomObject,
    CustomObjectDraft,
    FieldContainer,
    LineItem,
    LocalizedString,
    Money,
    Order,
    OrderAddReturnInfoAction,
    OrderFromCartDraft,
    OrderSetLineItemCustomFieldAction,
    OrderSetReturnItemCustomTypeAction,
    OrderSetReturnPaymentStateAction,
    OrderState,
    OrderTransitionLineItemStateAction,
    Payment,
    PaymentAddTransactionAction,
    PaymentDraft,
    PaymentMethodInfo,
    PaymentResourceIdentifier,
    PaymentSetTransactionCustomTypeAction,
    PaymentState,
    PaymentStatusDraft,
    ProductVariant,
    ReturnItemDraft,
    ReturnPaymentState,
    ReturnShipmentState,
    ShipmentState,
    State as LineItemState,
    StateResourceIdentifier,
    TaxMode,
    TransactionDraft,
    TransactionState,
    TransactionType,
    Type as CustomType,
    TypeDraft as CustomTypeDraft,
    TypeResourceIdentifier,
)

from django.conf import settings
from openedx_filters.exceptions import OpenEdxFilterException

from commerce_coordinator.apps.commercetools.catalog_info.constants import (
    DEFAULT_ORDER_EXPANSION,
    EDX_PAYPAL_PAYMENT_INTERFACE_NAME,
    EDX_STRIPE_PAYMENT_INTERFACE_NAME,
    EdXFieldNames,
    TwoUKeys,
)
from commerce_coordinator.apps.commercetools.catalog_info.foundational_types import (
    TwoUCustomTypes,
)
from commerce_coordinator.apps.commercetools.utils import (
    find_latest_refund,
    find_refund_transaction,
    handle_commercetools_error,
    translate_refund_status_to_transaction_status,
)
from commerce_coordinator.apps.core.constants import (
    ORDER_HISTORY_PER_SYSTEM_REQ_LIMIT,
)

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
             client(Client): A mock client for testing (ONLY).
        """
        super().__init__()

        config = settings.COMMERCETOOLS_CONFIG
        self.base_client = Client(
            client_id=config["clientId"],
            client_secret=config["clientSecret"],
            scope=config["scopes"].split(" "),
            url=config["apiUrl"],
            token_url=config["authUrl"],
            project_key=config["projectKey"],
        )

    def ensure_custom_type_exists(self, type_def: CustomTypeDraft) -> Optional[CustomType]:
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

    def tag_customer_with_lms_user_info(self, customer: Customer, lms_user_id: int, lms_user_name: str) -> Customer:
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
                CustomerSetCustomTypeAction(
                    type=TypeResourceIdentifier(
                        key=TwoUCustomTypes.CUSTOMER_TYPE_DRAFT.key,
                    ),
                    fields=FieldContainer(
                        {
                            EdXFieldNames.LMS_USER_ID: f"{lms_user_id}",
                            EdXFieldNames.LMS_USER_NAME: lms_user_name,
                        }
                    ),
                ),
            ],
        )

        return ret

    def get_customer_by_lms_user_id(self, lms_user_id: int) -> Optional[Customer]:
        """
        Get a Commercetools Customer by their LMS User ID

        Args:
            lms_user_id: edX LMS User ID

        Returns:
            Optional[Customer], A Commercetools Customer Object, or None if not found, may throw if more than one user
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

    def get_order_by_id(self, order_id: str, expand: ExpandList = DEFAULT_ORDER_EXPANSION) -> Order:
        """
        Fetch an order by the Order ID (UUID)

        Args:
            order_id (str): Order ID (UUID)
            expand: List of Order Parameters to expand

        Returns (Order): Order with Expanded Properties
        """
        logger.info(f"[CommercetoolsAPIClient] - Attempting to find order with id: {order_id}")
        return self.base_client.orders.get_by_id(order_id, expand=list(expand))

    def get_order_by_number(self, order_number: str, expand: ExpandList = DEFAULT_ORDER_EXPANSION) -> Order:
        """
        Fetch an order by the Order Number (Human readable order number)

        Args:
            order_number (str): Order Number (Human readable order number)
            expand: List of Order Parameters to expand

        Returns (Order): Order with Expanded Properties
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
    ) -> PaginatedResult[Order]:
        """
        Call commercetools API overview endpoint for data about historical orders.

        Args:
            customer (Customer): Commerce Tools Customer to look up orders for
            offset (int): Pagination Offset
            limit (int): Maximum number of results
            expand: List of Order Parameters to expand

        Returns:
            PaginatedResult[Order]: Dictionary representation of JSON returned from API

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
    ) -> (PaginatedResult[Order], Customer):
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

    def get_customer_by_id(self, customer_id: str) -> Customer:
        logger.info(f"[CommercetoolsAPIClient] - Attempting to find customer with ID {customer_id}")
        return self.base_client.customers.get_by_id(customer_id)

    def get_state_by_id(self, state_id: str) -> LineItemState:
        logger.info(f"[CommercetoolsAPIClient] - Attempting to find state with id {state_id}")
        return self.base_client.states.get_by_id(state_id)

    def get_state_by_key(self, state_key: str) -> LineItemState:
        logger.info(f"[CommercetoolsAPIClient] - Attempting to find state with key {state_key}")
        return self.base_client.states.get_by_key(state_key)

    def get_payment_by_key(self, payment_key: str) -> Payment:
        logger.info(f"[CommercetoolsAPIClient] - Attempting to find payment with key {payment_key}")
        return self.base_client.payments.get_by_key(payment_key)

    def get_payment_by_transaction_interaction_id(self, interaction_id: str) -> Payment:
        """
        Fetch a payment by the transaction interaction ID
        """
        logger.info(f"[CommercetoolsAPIClient] - Attempting to find payment with interaction ID {interaction_id}")
        return self.base_client.payments.query(where=f'transactions(interactionId="{interaction_id}")').results[0]

    def get_product_by_program_id(self, program_id: str) -> Optional[ProductVariant]:
        """
        Fetches a program product from Commercetools.
        Args:
            program_id: The ID of the program (bundle) to fetch.
        Returns:
            ProductVariant if found, None otherwise.
        """
        results = self.base_client.product_projections.search(False, filter=f'key:"{program_id}"').results

        return results[0] if results else None

    def get_product_variant_by_course_run(self, cr_id: str) -> Optional[ProductVariant]:
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

    def create_return_for_order(self, order_id: str, order_version: int, order_line_item_id: str) -> Order:
        """
        Creates refund/return for Commercetools order
        Args:
            order_id (str): Order ID (UUID)
            order_version (int): Current version of order
            order_line_item_id (str): ID of order line item
        Returns (Order): Updated order object or
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
    ) -> Union[Order, None]:
        """
        Update paymentState on the LineItemReturnItem attached to the order for enrollment code purchase.
        Updated by the Order ID (UUID)

        Args:
            order_id (str): Order ID (UUID)
            order_version (int): Current version of order
            return_line_item_return_id (str): LineItemReturnItem ID

        Returns (Order): Updated order object or
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
    ) -> Union[Order, None]:
        """
        Update paymentState on the LineItemReturnItem attached to the order.
        Updated by the Order ID (UUID)

        Args:
            order_id (str): Order ID (UUID)
            order_version (int): Current version of order
            return_line_item_return_id (str): LineItemReturnItem ID

        Returns (Order): Updated order object or
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
                    type=TypeResourceIdentifier(
                        key="returnItemCustomType",
                    ),
                    fields=FieldContainer(custom_fields),
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
                    type=TypeResourceIdentifier(key="transactionCustomType"),
                    fields=FieldContainer({"returnItemId": ', '.join(return_line_item_return_ids)}),
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
    ) -> Payment:
        """
        Create Commercetools payment transaction for refund
        Args:
            payment_id (str): Payment ID (UUID)
            payment_version (int): Current version of payment
            refund (Refund): Refund object
        Returns (Payment): Updated payment object or
        Raises Exception: Error if creation was unsuccessful.
        """
        try:
            logger.info(
                f"[CommercetoolsAPIClient] - Creating refund transaction for payment with ID {payment_id} "
                f"following successful refund {refund.get('id')} in PSP: {psp}"
            )
            refund = self._preprocess_refund_object(refund, psp)

            amount_as_money = Money(
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
    ) -> Order:
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
        Returns (Order): Updated order object or
        Returns (Order): Current un-updated order
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
        line_items: List[LineItem],
        from_state_id: str,
        new_state_key: str,
        use_state_id: bool = False,
    ) -> Order:
        """
        Update Commercetools order line item state for all items in one call.

        Args:
            order_id (str): Order ID (UUID)
            order_version (int): Current version of order
            line_items (List[object]): List of line item objects
            from_state_id (str): ID of LineItemState to transition from
            new_state_key (str): Key of LineItemState to transition to
            use_state_id (bool): Whether to use state ID or key for transition

        Returns:
            Updated order object or current un-updated order
        """

        if use_state_id:
            from_state_key = from_state_id  # only set for logging purposes
            from_state = StateResourceIdentifier(id=from_state_id)
        else:
            from_state_key = self.get_state_by_id(from_state_id).key
            from_state = StateResourceIdentifier(key=from_state_key)

        logger.info(
            f"[CommercetoolsAPIClient] - Transitioning line item states for order ID '{order_id}'. "
            f"From State: '{from_state_key}' "
            f"To State: '{new_state_key}' "
            f"Line Item IDs: {', '.join(item.id for item in line_items)}"
        )

        try:
            if use_state_id or new_state_key != from_state_key:
                actions = [
                    OrderTransitionLineItemStateAction(
                        line_item_id=item.id,
                        quantity=item.quantity,
                        from_state=from_state,
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
    ) -> Customer:
        """
        Update Commercetools customer with anonymized fields
        Args:
            customer_id (str): Customer ID (UUID)
            customer_version (int): Current version of customer
            retired_first_name (str): anonymized customer first name value
            retired_last_name (str): anonymized customer last name value
            retired_email (str): anonymized customer email value
            retired_lms_username (str): anonymized customer lms username value
        Returns (Customer): Updated customer object or
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

    def create_customer(
        self,
        *,
        email: str,
        first_name: str,
        last_name: str,
        lms_user_id: int,
        lms_username: str,
        is_email_verified=True,
    ) -> Customer:
        """
        Create a new customer in Commercetools with LMS user info

        Args:
            email (str): User's email address
            is_email_verified (bool): Whether email is verified
            first_name (str): User's first name
            last_name (str): User's last name
            lms_user_id (int): LMS user ID
            lms_username (str): LMS username

        Returns:
            The newly created customer
        """
        custom_fields_draft = CustomFieldsDraft(
            type=TypeResourceIdentifier(
                key=TwoUCustomTypes.CUSTOMER_TYPE_DRAFT.key,
            ),
            fields=FieldContainer(
                {
                    EdXFieldNames.LMS_USER_ID: str(lms_user_id),
                    EdXFieldNames.LMS_USER_NAME: lms_username,
                }
            ),
        )

        customer_draft = CustomerDraft(
            key=str(uuid.uuid4()),
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_email_verified=is_email_verified,
            authentication_mode=AuthenticationMode.EXTERNAL_AUTH,
            custom=custom_fields_draft,
        )

        try:
            customer = self.base_client.customers.create(customer_draft).customer
            logger.info(
                f"[CommercetoolsAPIClient] - Successfully created customer: {customer.id} for LMS user: {lms_user_id}"
            )
            return customer
        except CommercetoolsError as err:
            handle_commercetools_error(
                "[CommercetoolsAPIClient.create_customer]",
                err,
                f"Failed to create customer for LMS user: {lms_user_id}",
            )
            raise err

    def update_customer(
        self,
        *,
        customer: Customer,
        updates: dict[str, str | None],
    ) -> Customer:
        """
        Update customer information

        Args:
            customer (Customer): The customer to update
            updates (dict): Dictionary of attributes to update

        Returns:
            The updated customer
        """
        try:
            attr_to_update_action_map = {
                "first_name": lambda value: CustomerSetFirstNameAction(
                    first_name=value
                ),
                "last_name": lambda value: CustomerSetLastNameAction(
                    last_name=value
                ),
                "email": lambda value: CustomerChangeEmailAction(email=value),
                "lms_username": lambda value: CustomerSetCustomFieldAction(
                    name=EdXFieldNames.LMS_USER_NAME, value=value
                ),
            }

            updated_customer = self.base_client.customers.update_by_id(
                id=customer.id,
                version=customer.version,
                actions=[
                    attr_to_update_action_map[field](value)
                    for field, value in updates.items()
                ],
            )

            logger.info(
                "[CommercetoolsAPIClient] - Successfully updated "
                f"customer: {customer.id}"
            )

            return updated_customer
        except CommercetoolsError as err:
            handle_commercetools_error(
                "[CommercetoolsAPIClient.update_customer]",
                err,
                f"Failed to update customer: {customer.id}",
            )
            raise err

    def get_customer_cart(self, customer_id: str) -> Optional[Cart]:
        """
        Get the active cart for a customer if it exists

        Args:
            customer_id (str): The ID of the customer

        Returns:
            The active cart, or None if not found
        """
        try:
            cart = self.base_client.carts.get_by_customer_id(customer_id)
            logger.info(
                "[CommercetoolsAPIClient] - Active cart already exists "
                f"for customer: {customer_id}"
            )
            return cart
        except CommercetoolsError as err:
            if err.code == "ResourceNotFound":
                logger.info(
                    "[CommercetoolsAPIClient] - No active cart exists "
                    f"for customer: {customer_id}"
                )
                return None

            handle_commercetools_error(
                "[CommercetoolsAPIClient.get_customer_cart]",
                err,
                f"Error finding cart for customer {customer_id}",
            )
            raise err

    def delete_cart(self, cart: Cart) -> None:
        """
        Delete a cart of a customer

        Args:
            cart (Cart): The cart to delete
        """
        try:
            self.base_client.carts.delete_by_id(cart.id, cart.version)
            logger.info(
                "[CommercetoolsAPIClient] - Successfully deleted "
                f"cart: {cart.id} for customer: {cart.customer_id}"
            )

        except CommercetoolsError as err:
            handle_commercetools_error(
                "[CommercetoolsAPIClient.delete_cart]",
                err,
                f"Failed to delete cart: {cart.id} "
                f"for customer: {cart.customer_id}",
            )
            raise err

    def _get_order_number_custom_object(self) -> CustomObject:
        """
        Get the custom object that stores the order number counter

        Returns:
            Custom object with order number counter
        """
        try:
            return self.base_client.custom_objects.get_by_container_and_key(
                container=TwoUKeys.ORDER_NUMBER_CUSTOM_OBJECT_CONTAINER,
                key=TwoUKeys.ORDER_NUMBER_CUSTOM_OBJECT_KEY,
            )

        except CommercetoolsError as err:
            handle_commercetools_error(
                "[CommercetoolsAPIClient._get_order_number_custom_object]",
                err,
                "Failed to get order number custom object",
            )
            raise err

    def _update_order_number_custom_object(
        self,
        order_number_custom_object: CustomObject,
    ) -> CustomObject:
        """
        Update the order number counter, resetting to 1 if the year has changed

        Args:
            custom_object: The custom object containing the order number counter

        Returns:
            Updated custom object with incremented counter
        """

        current_year = datetime.datetime.now().year
        previous_order_year = order_number_custom_object.last_modified_at.year

        new_order_number = (
            1
            if current_year > previous_order_year
            else order_number_custom_object.value + 1
        )

        try:
            draft = CustomObjectDraft(
                container=TwoUKeys.ORDER_NUMBER_CUSTOM_OBJECT_CONTAINER,
                key=TwoUKeys.ORDER_NUMBER_CUSTOM_OBJECT_KEY,
                value=new_order_number,
                version=order_number_custom_object.version,
            )
            return self.base_client.custom_objects.create_or_update(draft)
        except CommercetoolsError as err:
            handle_commercetools_error(
                "[CommercetoolsAPIClient._update_order_number]",
                err,
                "Failed to update order number custom object",
            )
            raise err

    def get_new_order_number(self) -> str:
        """
        Get a new order number for cart

        Returns:
            str: A new order number with format "2U-YYYY#######" (year + 6-digit sequence)
        """
        order_number = self._get_order_number_custom_object()
        order_number = self._update_order_number_custom_object(order_number)

        order_prefix = f"2U-{datetime.datetime.now().year}"
        six_digit_number = str(order_number.value).zfill(6)
        new_order_number = order_prefix + six_digit_number

        logger.info(
            f"[CommercetoolsAPIClient] - Generated new order number: {new_order_number}"
        )

        return new_order_number

    def create_cart(
        self,
        *,
        customer: Customer,
        order_number: str,
        currency: str,
    ) -> Cart:
        """
        Create a new cart for a customer

        Args:
            customer (Customer): The customer for whom to create the cart
            order_number (str): The order number for the cart
            currency (str): Currency code for the cart
            country (str): Country code for the cart
            language (str): Language code for the cart

        Returns:
            Cart: The created cart object
        """
        try:
            custom_fields_draft = CustomFieldsDraft(
                type=TypeResourceIdentifier(key=TwoUKeys.ORDER_CUSTOM_TYPE),
                fields=FieldContainer({TwoUKeys.ORDER_ORDER_NUMBER: order_number}),
            )
            cart_draft = CartDraft(
                customer_id=customer.id,
                customer_email=customer.email,
                custom=custom_fields_draft,
                tax_mode=TaxMode.DISABLED,
                currency=currency,
            )

            expand = ["lineItems[*].productType.obj", "custom"]

            cart = self.base_client.carts.create(cart_draft, expand=expand)
            logger.info(
                f"[CommercetoolsAPIClient] - Successfully created new cart: {cart.id} for customer: {customer.id}"
            )
            return cart
        except CommercetoolsError as err:
            handle_commercetools_error(
                "[CommercetoolsAPIClient.create_cart]",
                err,
                f"Failed to create cart for customer: {customer.id}",
            )
            raise err

    def update_cart(
        self,
        *,
        external_price: Money,
        cart: Cart,
        sku: str,
        email_domain: str,
        payment_id: str,
    ) -> Cart:
        """
        Update the cart with a new line item and payment

        Args:
            external_price (Money): The price of the line item
            cart (Cart): The cart to update
            sku (str): The SKU of the line item
            email_domain (str): The email domain for the cart
            payment_id (str): The ID of the payment to add

        Returns:
            Cart: The updated cart object
        """
        try:
            address = BaseAddress(country="UNDEFINED")
            actions = [
                CartAddLineItemAction(sku=sku, external_price=external_price),
                CartSetCustomFieldAction(
                    name=TwoUKeys.ORDER_EMAIL_DOMAIN, value=email_domain
                ),
                CartSetCustomFieldAction(
                    name=TwoUKeys.ORDER_MOBILE_ORDER, value=True
                ),
                CartSetBillingAddressAction(address=address),
                CartSetShippingAddressAction(address=address),
                CartAddPaymentAction(
                    payment=PaymentResourceIdentifier(id=payment_id)
                ),
            ]
            expand = ["lineItems[*].productType.obj", "custom"]

            updated_cart = self.base_client.carts.update_by_id(
                id=cart.id, version=cart.version, actions=actions, expand=expand
            )
            logger.info(
                "[CommercetoolsAPIClient] - Successfully added items to "
                f"cart: {cart.id} for customer: {cart.customer_id}"
            )
            return updated_cart
        except CommercetoolsError as err:
            handle_commercetools_error(
                "[CommercetoolsAPIClient.add_to_cart]",
                err,
                f"Failed to add items to cart: {cart.id} "
                f"for customer: {cart.customer_id}",
            )
            raise err

    def _map_payment_status_to_transaction_state(
        self, payment_status: str  # pylint: disable=unused-argument
    ) -> TransactionState:
        """
        Maps the status from the payment processor to the transaction state in commercetools

        Args:
            payment_status (str): Status from the payment processor

        Returns:
            Transaction state in commercetools
        """
        # TODO: implement
        return TransactionState.SUCCESS

    def create_payment(
        self,
        *,
        amount_planned: Money,
        customer_id: str,
        payment_method: str,
        payment_processor: str,
        payment_status: str,
        psp_payment_id: str,
        psp_transaction_id: str,
        usd_cent_amount: int,
    ) -> Payment:
        """
        Create a new payment in Commercetools

        Args:
            amount_planned (Money): Amount planned for the payment
            customer_id (str): The ID of the customer
            payment_method (str): The payment method used
            payment_processor (str): The payment processor used
            payment_status (str): The status of the payment
            psp_payment_id (str): The ID of the payment in the PSP
            psp_transaction_id (str): The ID of the transaction in the PSP
            usd_cent_amount (int): Amount in cents

        Returns:
            Payment: The created payment object
        """
        payment_method_info = PaymentMethodInfo(
            payment_interface=payment_processor,
            method=payment_method,
            name=LocalizedString(name=payment_method),
        )
        # translate this based on mobile status codes
        payment_status_draft = PaymentStatusDraft(
            interface_code=payment_status,
            interface_text=payment_status,
        )
        transaction_draft = TransactionDraft(
            type=TransactionType.CHARGE,
            amount=amount_planned,
            state=self._map_payment_status_to_transaction_state(payment_status),
            interaction_id=psp_transaction_id,
            custom=CustomFieldsDraft(
                type=TypeResourceIdentifier(key=TwoUKeys.TRANSACTION_CUSTOM_TYPE),
                fields=FieldContainer(
                    {TwoUKeys.TRANSACTION_USD_AMOUNT: usd_cent_amount}
                ),
            ),
        )
        payment_draft = PaymentDraft(
            key=psp_payment_id,
            amount_planned=amount_planned,
            customer=CustomerResourceIdentifier(id=customer_id),
            interface_id=psp_payment_id,
            payment_method_info=payment_method_info,
            payment_status=payment_status_draft,
            transactions=[transaction_draft],
        )

        try:
            payment = self.base_client.payments.create(payment_draft)
            logger.info(
                f"[CommercetoolsAPIClient] - Created payment: {payment.id}"
                f"for customer: {customer_id}"
            )
            return payment
        except CommercetoolsError as err:
            handle_commercetools_error(
                "[CommercetoolsAPIClient.create_payment]",
                err,
                f"Unable to create payment for customer: {customer_id}",
            )
            raise err

    def create_order_from_cart(self, cart: Cart) -> Order:
        """
        Create a new order from a cart

        Args:
            cart (Cart): The cart to create the order from

        Returns:
            The created order object
        """
        try:
            order_number = cart.custom.fields.get(TwoUKeys.ORDER_ORDER_NUMBER)
            order_from_cart_draft = OrderFromCartDraft(
                id=cart.id,
                version=cart.version,
                order_number=order_number,
                order_state=OrderState.COMPLETE,
                payment_state=PaymentState.PAID,
                shipment_state=ShipmentState.SHIPPED,
            )

            order = self.base_client.orders.create(order_from_cart_draft)
            logger.info(
                f"[CommercetoolsAPIClient] - Successfully created new order: {order.id} "
                f"from cart: {cart.id} for customer: {cart.customer_id}"
            )
            return order
        except CommercetoolsError as err:
            handle_commercetools_error(
                "[CommercetoolsAPIClient.create_order_from_cart]",
                err,
                f"Failed to create order from cart: {cart.id}"
                f"for customer: {cart.customer_id}",
            )
            raise err
