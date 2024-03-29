"""
Commercetools filter pipelines
"""

from logging import getLogger

import attrs
from commercetools import CommercetoolsError
from commercetools.platform.models import Order as CTOrder
from openedx_filters import PipelineStep
from openedx_filters.exceptions import OpenEdxFilterException

from commerce_coordinator.apps.commercetools.catalog_info.edx_utils import get_edx_payment_intent_id
from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient
from commerce_coordinator.apps.commercetools.constants import COMMERCETOOLS_ORDER_MANAGEMENT_SYSTEM
from commerce_coordinator.apps.commercetools.data import order_from_commercetools
from commerce_coordinator.apps.core.constants import PipelineCommand
from commerce_coordinator.apps.core.exceptions import InvalidFilterType
from commerce_coordinator.apps.rollout.utils import is_commercetools_line_item_already_refunded

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


class FetchOrderDetails(PipelineStep):
    """ Fetch the order Details and if we can, set the PaymentIntent """

    # pylint: disable=unused-argument
    def run_filter(self, params, active_order_management_system, order_number):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Arguments:
            active_order_management_system: The Active Order System (optional)
            params: arguments passed through from the original order history url querystring
            order_number: Order number (for now this is an order.id, but this should change in the future)
            TODO: SONIC-277 (in-progress)
        Returns:
        """
        if active_order_management_system != COMMERCETOOLS_ORDER_MANAGEMENT_SYSTEM:
            return PipelineCommand.CONTINUE.value

        try:
            ct_api_client = CommercetoolsAPIClient()
            ct_order = ct_api_client.get_order_by_id(order_id=order_number)

            ret_val = {
                "order_data": ct_order
            }

            intent_id = get_edx_payment_intent_id(ct_order)

            if intent_id:
                ret_val['payment_intent_id'] = intent_id

            return ret_val
        except CommercetoolsError as err:  # pragma no cover
            log.exception(f"[{type(self).__name__}] Commercetools Error: {err}, {err.errors}")
            return PipelineCommand.CONTINUE.value


class CreateReturnForCommercetoolsOrder(PipelineStep):
    """
    Creates refund/return for Commercetools order by Updating its
    ReturnShipmentStatus & ReturnPaymentStatus
    """

    def run_filter(
            self,
            active_order_management_system,
            order_number,
            order_line_id
    ):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Args:
            active_order_management_system: The Active Order System
            order_number: Order number (for now this is an order.id, but this should change in the future)
            TODO: SONIC-277 (in-progress)
            order_line_id: ID of order line item
        Returns:
            returned_order: Updated Commercetools order
            returned_line_item_return_id: Updated Commercetools order's return item ID

        """
        if active_order_management_system != COMMERCETOOLS_ORDER_MANAGEMENT_SYSTEM:  # pragma no cover
            return PipelineCommand.CONTINUE.value

        try:
            ct_api_client = CommercetoolsAPIClient()
            order = ct_api_client.get_order_by_id(order_id=order_number)
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


class UpdateCommercetoolsOrderReturnPaymentStatus(PipelineStep):
    """
    Updates the ReturnPaymentStatus of a Commercetools order
    """
    def run_filter(self, returned_order: CTOrder, return_line_item_return_id: str):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Arguments:
            returned_order: preliminary order (from an earlier pipeline step) we want to append to
            return_line_item_return_id: id of the LineItemReturnItem to be refunded
        Returns:
            returned_order: the modifed CT order
        """

        ct_api_client = CommercetoolsAPIClient()
        updated_order = ct_api_client.update_return_payment_state_after_successful_refund(
            order_id=returned_order.id,
            order_version=returned_order.version,
            return_line_item_return_id=return_line_item_return_id
        )

        return {
            "returned_order": updated_order
        }
