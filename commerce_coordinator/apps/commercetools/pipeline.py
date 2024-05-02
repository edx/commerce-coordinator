"""
Commercetools filter pipelines
"""
import decimal
from logging import getLogger

import attrs
from commercetools import CommercetoolsError
from commercetools.platform.models import Order as CTOrder
from openedx_filters import PipelineStep
from openedx_filters.exceptions import OpenEdxFilterException
from requests import HTTPError

from commerce_coordinator.apps.commercetools.catalog_info.edx_utils import (
    get_edx_payment_intent_id,
    get_edx_refund_amount
)
from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient
from commerce_coordinator.apps.commercetools.constants import COMMERCETOOLS_ORDER_MANAGEMENT_SYSTEM
from commerce_coordinator.apps.commercetools.data import order_from_commercetools
from commerce_coordinator.apps.commercetools.utils import has_refund_transaction
from commerce_coordinator.apps.core.constants import PipelineCommand
from commerce_coordinator.apps.core.exceptions import InvalidFilterType
from commerce_coordinator.apps.rollout.utils import (
    get_order_return_info_return_items,
    is_commercetools_line_item_already_refunded
)

log = getLogger(__name__)


class GetCommercetoolsOrders(PipelineStep):
    """
    Adds commercetools orders to the order data list.
    """

    def run_filter(self, params, order_data):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Arguments:
            params: arguments passed through from the original order history url querystring
            order_data: any preliminary orders (from an earlier pipeline step) we want to append to
        Returns:
        """

        try:
            ct_api_client = CommercetoolsAPIClient()
            ct_orders = ct_api_client.get_orders_for_customer(
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
        except HTTPError as err:
            log.exception(f"[{type(self).__name__}] HTTP Error: {err}")
            return PipelineCommand.CONTINUE.value


class FetchOrderDetails(PipelineStep):
    """ Fetch the order Details and if we can, set the PaymentIntent """

    def run_filter(self, active_order_management_system, order_number, **kwargs):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Arguments:
            active_order_management_system: The Active Order System (optional)
            params: arguments passed through from the original order history url querystring
            order_number: Order number
        Returns:
        """
        if active_order_management_system != COMMERCETOOLS_ORDER_MANAGEMENT_SYSTEM:
            return PipelineCommand.CONTINUE.value

        try:
            ct_api_client = CommercetoolsAPIClient()
            ct_order = ct_api_client.get_order_by_id(order_id=order_number)

            ret_val = {
                "order_data": ct_order,
                "order_id": ct_order.id
            }

            intent_id = get_edx_payment_intent_id(ct_order)

            if intent_id:
                ct_payment = ct_api_client.get_payment_by_key(intent_id)
                ret_val['payment_intent_id'] = intent_id
                ret_val['amount_in_cents'] = get_edx_refund_amount(ct_order)
                ret_val['has_been_refunded'] = has_refund_transaction(ct_payment)
                ret_val['payment_data'] = ct_payment
            else:
                ret_val['payment_intent_id'] = None
                ret_val['amount_in_cents'] = decimal.Decimal(0.00)
                ret_val['has_been_refunded'] = False
                ret_val['payment_data'] = None

            return ret_val
        except CommercetoolsError as err:  # pragma no cover
            log.exception(f"[{type(self).__name__}] Commercetools Error: {err}, {err.errors}")
            return PipelineCommand.CONTINUE.value
        except HTTPError as err:
            log.exception(f"[{type(self).__name__}] HTTP Error: {err}")
            return PipelineCommand.CONTINUE.value


class FetchOrderDetailsID(PipelineStep):
    """ Fetch the order Details and if we can, set the PaymentIntent """

    def run_filter(self, active_order_management_system, order_id, **kwargs):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Arguments:
            active_order_management_system: The Active Order System (optional)
            params: arguments passed through from the original order history url querystring
            order_number: Order number
        Returns:
        """

        if active_order_management_system != COMMERCETOOLS_ORDER_MANAGEMENT_SYSTEM:
            return PipelineCommand.CONTINUE.value

        try:
            ct_api_client = CommercetoolsAPIClient()
            ct_order = ct_api_client.get_order_by_id(order_id=order_id)

            ret_val = {
                "order_data": ct_order,
                "order_id": ct_order.id
            }

            intent_id = get_edx_payment_intent_id(ct_order)

            if intent_id:
                ret_val['payment_intent_id'] = intent_id
                ret_val['amount_in_cents'] = get_edx_refund_amount(ct_order)
                ret_val['has_been_refunded'] = len(get_order_return_info_return_items(ct_order)) >= 1
            else:
                ret_val['payment_intent_id'] = None
                ret_val['amount_in_cents'] = decimal.Decimal(0.00)
                ret_val['has_been_refunded'] = False

            return ret_val
        except CommercetoolsError as err:  # pragma no cover
            log.exception(f"[{type(self).__name__}] Commercetools Error: {err}, {err.errors}")
            return PipelineCommand.CONTINUE.value
        except HTTPError as err:
            log.exception(f"[{type(self).__name__}] HTTP Error: {err}")
            return PipelineCommand.CONTINUE.value


class CreateReturnForCommercetoolsOrder(PipelineStep):
    """
    Creates refund/return for Commercetools order by Updating its
    ReturnShipmentStatus & ReturnPaymentStatus
    """

    def run_filter(
        self,
        active_order_management_system,
        order_line_id,
        order_data: CTOrder,
        has_been_refunded=False,
        **kwargs
    ):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Args:
            has_been_refunded(bool): Whether or not the order has been refunded
            order_data:(CTOrder): Commercetools order object
            active_order_management_system: The Active Order System
            order_number: Order number (for now this is an order.id, but this should change in the future)
            order_line_id: ID of order line item
        Returns:
            returned_order: Updated Commercetools order
            returned_line_item_return_id: Updated Commercetools order's return item ID

        """
        if active_order_management_system != COMMERCETOOLS_ORDER_MANAGEMENT_SYSTEM:  # pragma no cover
            return PipelineCommand.CONTINUE.value

        if has_been_refunded:  # pragma no cover
            return PipelineCommand.CONTINUE.value

        try:
            ct_api_client = CommercetoolsAPIClient()
            order = order_data
            if not is_commercetools_line_item_already_refunded(order, order_line_id):
                returned_order = ct_api_client.create_return_for_order(
                    order_id=order.id,
                    order_version=order.version,
                    order_line_id=order_line_id
                )

                returned_line_item_return_id = returned_order.return_info[0].items[0].id

                return {
                    'returned_order': returned_order,
                    'returned_line_item_return_id': returned_line_item_return_id
                }
            else:
                log.exception(f'Refund already created for order {order.id} with '
                              f'order line id {order_line_id}')
                raise InvalidFilterType(
                    f'Refund already created for order {order.id} with '
                    f'order line id {order_line_id}')
        except CommercetoolsError as err:  # pragma no cover
            # TODO: FIX Per SONIC-354
            log.exception(f"[{type(self).__name__}] Commercetools Error: {err}, {err.errors}")
            raise OpenEdxFilterException(str(err)) from err
        except HTTPError as err:
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
            returned_order: preliminary order (from an earlier pipeline step) we want to append to
            return_line_item_return_id: id of the LineItemReturnItem to be refunded
        Returns:
            returned_order: the modifed CT order
        """

        # 'returned_order' is only sent if we're on an automatic refunds flow.
        if 'returned_order' not in kwargs:
            order = kwargs['order_data']
            return_item_id = get_order_return_info_return_items(order)[0].id
        else:
            order = kwargs['returned_order']
            return_item_id = kwargs['return_line_item_return_id']

        ct_api_client = CommercetoolsAPIClient()
        updated_order = ct_api_client.update_return_payment_state_after_successful_refund(
            order_id=order.id,
            order_version=order.version,
            return_line_item_return_id=return_item_id
        )

        return {
            "returned_order": updated_order
        }


class CreateReturnPaymentTransaction(PipelineStep):
    """
    Creates a Transaction for a return payment of a Commercetools order
    based on Stripes refund object on a refunded charge.
    """

    def run_filter(
        self,
        payment_data,
        refund_response,
        active_order_management_system,
        has_been_refunded,
        **kwargs
    ):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Arguments:
            payment_data: CT payment object attached to the refunded order
            refund_response: Stripe refund object or str value "charge_already_refunded"
            active_order_management_system: The Active Order System
            kwargs: arguments passed through from the filter.
            has_been_refunded(bool): Whether or not the order has been refunded
        Returns:
            returned_payment: the modifed CT payment
        """

        tag = type(self).__name__

        if active_order_management_system != COMMERCETOOLS_ORDER_MANAGEMENT_SYSTEM:  # pragma no cover
            return PipelineCommand.CONTINUE.value

        if refund_response == "charge_already_refunded" or has_been_refunded:
            return PipelineCommand.CONTINUE.value

        ct_api_client = CommercetoolsAPIClient()
        try:
            if payment_data is not None:
                payment_on_order = payment_data
            else:
                payment_key = refund_response['payment_intent']
                payment_on_order = ct_api_client.get_payment_by_key(payment_key)

            updated_payment = ct_api_client.create_return_payment_transaction(
                payment_id=payment_on_order.id,
                payment_version=payment_on_order.version,
                stripe_refund=refund_response
            )

            return {
                'returned_payment': updated_payment
            }
        except CommercetoolsError as err:  # pragma no cover
            log.exception(f"[{tag}] Commercetools Error: {err}, {err.errors}")
            return PipelineCommand.CONTINUE.value
        except HTTPError as err:  # pragma no cover
            log.exception(f"[{tag}] HTTP Error: {err}")
            return PipelineCommand.CONTINUE.value
