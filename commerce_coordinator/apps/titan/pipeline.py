"""
Pipelines for Titan
"""

import logging

from openedx_filters import PipelineStep
from requests import HTTPError

from commerce_coordinator.apps.titan.clients import TitanAPIClient
from commerce_coordinator.apps.titan.exceptions import NoActiveOrder, PaymentNotFound

logger = logging.getLogger(__name__)


class CreateTitanOrder(PipelineStep):
    """
    Adds titan orders to the order data list.
    """

    def run_filter(self, params, order_data):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Arguments:
            params: arguments passed through from the original order history url querystring
            order_data: any preliminary orders (from earlier pipeline step) we want to append to
        """

        titan_api_client = TitanAPIClient()
        titan_response = titan_api_client.create_order(**params)

        order_data.append(titan_response)

        return {
            "order_data": order_data
        }


class GetTitanPayment(PipelineStep):
    """
    Adds Titan's payment in payment data list.
    """

    def run_filter(self, edx_lms_user_id, payment_number):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Args:
            edx_lms_user_id: The edx.org LMS user ID of the user receiving the order.
            payment_number: The Payment identifier in Spree.

        """

        api_client = TitanAPIClient()
        try:
            payment = api_client.get_payment(
                edx_lms_user_id=edx_lms_user_id,
                payment_number=payment_number
            )
        except HTTPError as exc:
            logger.exception("[GetTitanPayment] Payment %s not found for user: %s", payment_number, edx_lms_user_id)
            raise PaymentNotFound from exc
        return payment


class GetTitanActiveOrder(PipelineStep):
    """
    Adds Titan's active order in payment data list
    """

    def run_filter(self, edx_lms_user_id):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Args:
            edx_lms_user_id: The edx.org LMS user ID of the user receiving the order.

        """
        api_client = TitanAPIClient()
        try:
            order = api_client.get_active_order(
                edx_lms_user_id=edx_lms_user_id
            )
        except HTTPError as e:
            logger.exception("[GetTitanActiveOrder] The specified user %s does not have an active order",
                             edx_lms_user_id)
            raise NoActiveOrder from e
        return order
