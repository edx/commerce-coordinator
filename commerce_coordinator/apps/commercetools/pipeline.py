"""
Commercetools filter pipelines
"""
from abc import abstractmethod
from logging import getLogger

from commercetools import CommercetoolsError
from openedx_filters import PipelineStep

from commerce_coordinator.apps.commercetools.catalog_info.constants import (
    EDX_STRIPE_PAYMENT_INTERFACE_NAME,
    PAYMENT_STATUS_INTERFACE_CODE_SUCCEEDED
)
from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient
from commerce_coordinator.apps.commercetools.constants import COMMERCETOOLS_ORDER_MANAGEMENT_SYSTEM
from commerce_coordinator.apps.commercetools.data import order_from_commercetools
from commerce_coordinator.apps.core.constants import PipelineCommand

log = getLogger(__name__)


class CommercetoolsPipelineStep(PipelineStep):
    """ Commercetools Pipeline Step """

    # noinspection PyMethodMayBeStatic
    def return_command_for_error(self, _error: CommercetoolsError) -> PipelineCommand:
        """
        Return a PipelineCommand if we error
        Args:
            _error: The exception

        Returns: CONTINUE or HALT

        """
        return PipelineCommand.CONTINUE

    @abstractmethod
    def run_safe_filter(self, **kwargs):
        """
        Abstract pipeline step runner.

        Used to implement custom code that'll be executed by OpenEdxPublicFilter's pipeline runner.
        It must be implemented by child classes.
        """
        log.warning(
            "PipelineStep run_safe_filter method not implemented.\n"
            "Child classes must implement this method with their custom code.\n"
            "By design, the pipeline expects either of three (3) types of returns:\n"
            "1. A dictionary with the arguments the method received. They can be modified in the process.\n"
            "2. None. Returning this will stop the pipeline execution. The accumulated output until "
            "this moment will be returned.\n"
            "3. An object different from a dict. Returning this will stop the pipeline execution. "
            "The accumulated output until this moment will be returned.\n"
        )

    def run_filter(self, **kwargs):
        try:
            return self.run_safe_filter(**kwargs)
        except CommercetoolsError as err:
            log.exception(f"Commercetools Error: {err}, {err.errors}", err)
            return self.return_command_for_error(err).value


class GetCommercetoolsOrders(CommercetoolsPipelineStep):
    """
    Adds commercetools orders to the order data list.
    """

    def run_safe_filter(self, params, order_data):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Arguments:
            params: arguments passed through from the original order history url querystring
            order_data: any preliminary orders (from an earlier pipeline step) we want to append to
        Returns:
        """

        ct_api_client = CommercetoolsAPIClient()
        ct_orders = ct_api_client.get_orders_for_customer(
            edx_lms_user_id=params["edx_lms_user_id"],
            limit=params["page_size"],
            offset=params["page"] * params["page_size"]
        )

        converted_orders = [order_from_commercetools(x, ct_orders[1])
                            for x in ct_orders[0].results]

        order_data.append(
            ct_orders[0].rebuild(converted_orders)
        )

        return {
            "order_data": order_data
        }


class FetchOrderDetails(CommercetoolsPipelineStep):
    """ Fetch the order Details and if we can, set the PaymentIntent """

    def run_safe_filter(self, active_order_management_system, order_number):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Arguments:
            active_order_management_system: The Active Order System (optional)
            params: arguments passed through from the original order history url querystring
            order_number: Order number (for now this is an order.id, but this should change in the future)
        Returns:
        """
        if not active_order_management_system == COMMERCETOOLS_ORDER_MANAGEMENT_SYSTEM and \
                active_order_management_system is not None:
            return PipelineCommand.CONTINUE.value

        ct_api_client = CommercetoolsAPIClient()
        ct_order = ct_api_client.get_order_by_id(order_id=order_number)

        ret_val = {
            "order_data": ct_order
        }

        for pr in ct_order.payment_info.payments:
            pmt = pr.obj
            if pmt.payment_status.interface_code == PAYMENT_STATUS_INTERFACE_CODE_SUCCEEDED \
                and pmt.payment_method_info.payment_interface == EDX_STRIPE_PAYMENT_INTERFACE_NAME and \
                    pmt.interface_id:
                ret_val['payment_intent_id'] = pmt.interface_id

        return ret_val
