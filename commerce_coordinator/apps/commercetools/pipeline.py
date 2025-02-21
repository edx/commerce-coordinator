"""
Commercetools filter pipelines
"""
import decimal
from datetime import datetime
from logging import getLogger

import attrs
from commercetools import CommercetoolsError
from django.conf import settings
from openedx_filters import PipelineStep
from openedx_filters.exceptions import OpenEdxFilterException
from requests import HTTPError

from commerce_coordinator.apps.commercetools.catalog_info.constants import (
    EDX_PAYPAL_PAYMENT_INTERFACE_NAME,
    EDX_STRIPE_PAYMENT_INTERFACE_NAME
)
from commerce_coordinator.apps.commercetools.catalog_info.edx_utils import (
    get_edx_refund_info,
    get_edx_successful_payment_info
)
from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient
from commerce_coordinator.apps.commercetools.constants import COMMERCETOOLS_ORDER_MANAGEMENT_SYSTEM
from commerce_coordinator.apps.commercetools.data import order_from_commercetools
from commerce_coordinator.apps.commercetools.utils import create_retired_fields, has_full_refund_transaction
from commerce_coordinator.apps.core.constants import PipelineCommand
from commerce_coordinator.apps.core.exceptions import InvalidFilterType
from commerce_coordinator.apps.rollout.utils import (
    get_order_return_info_return_items,
    is_commercetools_line_item_already_refunded
)
from commerce_coordinator.apps.rollout.waffle import is_redirect_to_commercetools_enabled_for_user

log = getLogger(__name__)


class GetCommercetoolsOrders(PipelineStep):
    """
    Adds commercetools orders to the order data list.
    """

    def run_filter(self, request, params, order_data):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Arguments:
            request: request object passed through from the lms filter
            params: arguments passed through from the original order history url querystring
            order_data: any preliminary orders (from an earlier pipeline step) we want to append to
        Returns:
        """
        if not is_redirect_to_commercetools_enabled_for_user(request):
            return PipelineCommand.CONTINUE.value

        try:
            ct_api_client = CommercetoolsAPIClient()
            ct_orders = ct_api_client.get_orders_for_customer(
                customer_id=params["customer_id"],
                email=params["email"],
                username=params["username"],
                edx_lms_user_id=params["edx_lms_user_id"],
                limit=params["page_size"],
                offset=params["page"] * params["page_size"]
            )

            # noinspection PyTypeChecker
            converted_orders = [attrs.asdict(order_from_commercetools(x, ct_orders[1]))
                                for x in ct_orders[0].results]

            order_data.append(
                ct_orders[0].rebuild(converted_orders)
            )

            return {
                "order_data": order_data
            }
        except CommercetoolsError as err:  # pragma no cover
            log.exception(f"[{type(self).__name__}] Commercetools Error: {err}, {err.errors}")
            return PipelineCommand.CONTINUE.value
        except ValueError as err:  # pragma no cover
            log.exception(f"[{type(self).__name__}] Value Error: {err}")
            return PipelineCommand.CONTINUE.value
        except HTTPError as err:
            log.exception(f"[{type(self).__name__}] HTTP Error: {err}")
            return PipelineCommand.CONTINUE.value


class FetchOrderDetailsByOrderNumber(PipelineStep):
    """ Fetch the order Details and if we can, set the PaymentIntent """

    def run_filter(self, active_order_management_system, order_number, **kwargs):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Arguments:
            active_order_management_system: The Active Order System
            order_number: Order number
            kwargs: The keyword arguments passed through from the filter
        Returns:
            order_data (CTOrder): The object of the order
            payment_intent_id (str): The Stripe PaymentIntent ID
            amount_in_cents (decimal): Total amount to refund
            has_been_refunded (bool): Has this payment been refunded
            payment_data (CTPayment): Payment object of the order
        """
        if active_order_management_system != COMMERCETOOLS_ORDER_MANAGEMENT_SYSTEM:
            return PipelineCommand.CONTINUE.value

        try:
            ct_api_client = CommercetoolsAPIClient()
            start_time = datetime.now()
            ct_order = ct_api_client.get_order_by_number(order_number=order_number)
            duration = (datetime.now() - start_time).total_seconds()
            log.info(f"[Performance Check] get_order_by_number call took {duration} seconds")

            payment, psp = get_edx_successful_payment_info(ct_order)

            ret_val = {
                "order_data": ct_order,
                "psp": psp,
                "payment_intent_id": payment.interface_id if payment else None
            }

            return ret_val
        except CommercetoolsError as err:  # pragma no cover
            log.exception(f"[{type(self).__name__}] Commercetools Error: {err}, {err.errors}")
            return PipelineCommand.CONTINUE.value
        except HTTPError as err:
            log.exception(f"[{type(self).__name__}] HTTP Error: {err}")
            return PipelineCommand.CONTINUE.value


class FetchOrderDetailsByOrderID(PipelineStep):
    """ Fetch the order details and if we can, set the PaymentIntent """

    def run_filter(
        self, active_order_management_system, order_id, return_line_item_id, **kwargs
    ):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Arguments:
            active_order_management_system: The Active Order System
            order_id: Order ID
            kwargs: The keyword arguments passed through from the filter
        Returns:
            order_data (CTOrder): The object of the order
            order_id (str): Order ID
            payment_intent_id (str): The Stripe PaymentIntent ID
            amount_in_cents (decimal): Total amount to refund
            has_been_refunded (bool): Has this payment been refunded
            payment_data (CTPayment): Payment object of the order
        """

        if active_order_management_system != COMMERCETOOLS_ORDER_MANAGEMENT_SYSTEM:
            return PipelineCommand.CONTINUE.value

        try:
            ct_api_client = CommercetoolsAPIClient()
            start_time = datetime.now()
            ct_order = ct_api_client.get_order_by_id(order_id=order_id)
            duration = (datetime.now() - start_time).total_seconds()
            log.info(f"[Performance Check] get_order_by_id call took {duration} seconds")

            payment, psp = get_edx_successful_payment_info(ct_order)

            ret_val = {
                "order_data": ct_order,
                "order_id": ct_order.id,
                "psp": psp,
                "payment_intent_id": payment.interface_id
            }

            if payment:
                ct_payment = ct_api_client.get_payment_by_key(payment.interface_id)
                refund_amount, ct_transaction_interaction_id = get_edx_refund_info(
                    ct_payment, ct_order, return_line_item_id)
                ret_val['amount_in_cents'] = refund_amount
                ret_val['ct_transaction_interaction_id'] = ct_transaction_interaction_id
                ret_val['has_been_refunded'] = is_commercetools_line_item_already_refunded(
                    ct_order, return_line_item_id) or has_full_refund_transaction(ct_payment)
                ret_val['payment_data'] = ct_payment
            else:
                ret_val['amount_in_cents'] = decimal.Decimal(0.00)
                ret_val['ct_transaction_interaction_id'] = None
                ret_val['has_been_refunded'] = False
                ret_val['payment_data'] = None

            return ret_val
        except CommercetoolsError as err:  # pragma no cover
            log.exception(f"[{type(self).__name__}] Commercetools Error: {err}, {err.errors}")
            return PipelineCommand.CONTINUE.value
        except HTTPError as err:
            log.exception(f"[{type(self).__name__}] HTTP Error: {err}")
            return PipelineCommand.CONTINUE.value


class CreateReturnForCommercetoolsOrder(PipelineStep):
    """
    Creates refund/return for Commercetools order by updating its
    ReturnShipmentStatus & ReturnPaymentStatus
    """

    def run_filter(
        self,
        active_order_management_system,
        order_id,
        order_line_item_id,
    ):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Args:
            active_order_management_system: The Active Order System
            order_id: Order ID
            order_line_item_id: Order's line item ID
        Returns:
            returned_order (CTOrder): Updated Commercetools order
            returned_line_item_return_id (str): Updated Commercetools order's return item ID

        """
        tag = type(self).__name__

        if active_order_management_system != COMMERCETOOLS_ORDER_MANAGEMENT_SYSTEM:  # pragma no cover
            return PipelineCommand.CONTINUE.value

        try:
            ct_api_client = CommercetoolsAPIClient()
            order = ct_api_client.get_order_by_id(order_id=order_id)

            if not is_commercetools_line_item_already_refunded(order, order_line_item_id):
                returned_order = ct_api_client.create_return_for_order(
                    order_id=order.id,
                    order_version=order.version,
                    order_line_item_id=order_line_item_id
                )

                returned_line_item_return_id = returned_order.return_info[0].items[0].id

                return {
                    'returned_order': returned_order,
                    'returned_line_item_return_id': returned_line_item_return_id
                }
            else:
                log.exception(f'Refund already created for order {order.id} with '
                              f'order line item id {order_line_item_id}')
                raise InvalidFilterType(
                    f'Refund already created for order {order.id} with '
                    f'order line item id {order_line_item_id}')
        except CommercetoolsError as err:  # pragma no cover
            # TODO: FIX Per SONIC-354
            log.info(f"[{tag}] Unsuccessful attempt to create order return with details: "
                     f"[order_id: {order_id}, order_line_item_id: {order_line_item_id}")
            log.exception(f"[{type(self).__name__}] Commercetools Error: {err}, {err.errors}")
            raise OpenEdxFilterException(str(err)) from err
        except HTTPError as err:  # pragma no cover
            log.info(f"[{tag}] Unsuccessful attempt to create order return with details: "
                     f"[order_id: {order_id}, order_line_item_id: {order_line_item_id}")
            log.exception(f"[{type(self).__name__}] HTTP Error: {err}")
            return PipelineCommand.CONTINUE.value


class UpdateCommercetoolsOrderReturnPaymentStatus(PipelineStep):
    """
    Updates the ReturnPaymentStatus of a Commercetools order
    """

    def run_filter(
        self,
        **kwargs
    ):
        """
        Execute a filter with the signature specified.
        Arguments:
            kwargs: The keyword arguments passed through from the filter
        Returns:
            returned_order: the modified CT order
        """

        order = kwargs['order_data']
        if 'return_line_item_return_id' not in kwargs:
            return_line_item_return_id = get_order_return_info_return_items(order)[0].id
        else:
            return_line_item_return_id = kwargs['return_line_item_return_id']

        ct_api_client = CommercetoolsAPIClient()
        updated_order = ct_api_client.update_return_payment_state_after_successful_refund(
            order_id=order.id,
            order_version=order.version,
            return_line_item_return_id=return_line_item_return_id,
            payment_intent_id=kwargs['payment_intent_id'],
            amount_in_cents=kwargs['amount_in_cents']
        )

        return {
            "returned_order": updated_order
        }


class CreateReturnPaymentTransaction(PipelineStep):
    """
    Creates a Transaction for a return payment of a Commercetools order
    based on PSP refund object on a refunded charge.
    """

    def run_filter(
        self,
        active_order_management_system,
        payment_data,
        has_been_refunded,
        payment_intent_id,
        psp,
        refund_response=None,
        **kwargs
    ):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Arguments:
            refund_response: PSP refund object or str value "charge_already_refunded"
            active_order_management_system: The Active Order System
            payment_data: CT payment object attached to the refunded order
            has_been_refunded (bool): Has this payment been refunded
            kwargs: arguments passed through from the filter.
        Returns:
            returned_payment: the modified CT payment
        """

        tag = type(self).__name__

        if active_order_management_system != COMMERCETOOLS_ORDER_MANAGEMENT_SYSTEM:  # pragma no cover
            log.info(f"[{tag}] active order management system is not {COMMERCETOOLS_ORDER_MANAGEMENT_SYSTEM}, skipping")
            return PipelineCommand.CONTINUE.value

        if refund_response == "charge_already_refunded" or has_been_refunded:
            log.info(f"[{tag}] refund has already been processed, skipping refund payment transaction creation")
            return PipelineCommand.CONTINUE.value

        ct_api_client = CommercetoolsAPIClient()
        try:
            payment_on_order = None
            if payment_data is not None:
                payment_on_order = payment_data
            elif psp == EDX_STRIPE_PAYMENT_INTERFACE_NAME:
                payment_key = refund_response['payment_intent']
                payment_on_order = ct_api_client.get_payment_by_key(payment_key)
            elif psp == EDX_PAYPAL_PAYMENT_INTERFACE_NAME:
                payment_on_order = ct_api_client.get_payment_by_key(payment_intent_id)

            updated_payment = ct_api_client.create_return_payment_transaction(
                payment_id=payment_on_order.id,
                payment_version=payment_on_order.version,
                refund=refund_response,
                psp=psp,
            )

            return {
                'returned_payment': updated_payment
            }
        except CommercetoolsError as err:  # pragma no cover
            error_message = "unknown"
            if psp == EDX_STRIPE_PAYMENT_INTERFACE_NAME:
                error_message = f"[stripe_payment_intent_id: {refund_response['payment_intent']}, "
            elif psp == EDX_PAYPAL_PAYMENT_INTERFACE_NAME:
                error_message = f"[paypal_capture_id: {refund_response['paypal_capture_id']}, "
            log.info(f"[{tag}] Unsuccessful attempt to create refund payment transaction with details: "
                     f"psp: {psp}, "
                     f"{error_message}"
                     f"payment_id: {payment_on_order.id}], message_id: {kwargs['message_id']}")
            log.exception(f"[{tag}] Commercetools Error: {err}, {err.errors}")
            return PipelineCommand.CONTINUE.value
        except HTTPError as err:  # pragma no cover
            error_message = "unknown"
            if psp == EDX_STRIPE_PAYMENT_INTERFACE_NAME:
                error_message = f"[stripe_payment_intent_id: {refund_response['payment_intent']}, "
            elif psp == EDX_PAYPAL_PAYMENT_INTERFACE_NAME:
                error_message = f"[paypal_capture_id: {refund_response['paypal_capture_id']}, "
            log.info(f"[{tag}] Unsuccessful attempt to create refund payment transaction with details: "
                     f"psp: {psp}, "
                     f"{error_message}"
                     f"payment_id: {payment_on_order.id}], message_id: {kwargs['message_id']}")
            log.exception(f"[{tag}] HTTP Error: {err}")
            return PipelineCommand.CONTINUE.value


class AnonymizeRetiredUser(PipelineStep):
    """
    Finds a CT customer by their LMS user ID and anonymizes PII fields
    following user retirement/account deletion in LMS
    """

    def run_filter(
        self,
        lms_user_id
    ):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Arguments:
            lms_user_id: User UUID from LMS connecting to and
            stored in CT customer object
        Returns:
            returned_customer: the modified CT customer
        """

        tag = type(self).__name__

        ct_api_client = CommercetoolsAPIClient()
        try:
            customer = ct_api_client.get_customer_by_lms_user_id(lms_user_id)
            first_name = customer.first_name
            last_name = customer.last_name
            email = customer.email
            lms_username = customer.custom.fields.get("edx-lms_user_name")
            fields_to_anonymize = {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "lms_username": lms_username
            }

            anonymized_fields = {key: create_retired_fields(value, settings.RETIRED_USER_SALTS)
                                 for key, value in fields_to_anonymize.items()}

            retired_customer = ct_api_client.retire_customer_anonymize_fields(
                customer.id,
                customer.version,
                anonymized_fields.get("first_name"),
                anonymized_fields.get("last_name"),
                anonymized_fields.get("email"),
                anonymized_fields.get("lms_username")
            )

            return {
                'returned_customer': retired_customer
            }
        except CommercetoolsError as err:  # pragma no cover
            log.exception(f"[{tag}] Commercetools Error: {err}, {err.errors}")
            return PipelineCommand.CONTINUE.value
        except HTTPError as err:  # pragma no cover
            log.exception(f"[{tag}] HTTP Error: {err}")
            return PipelineCommand.CONTINUE.value
