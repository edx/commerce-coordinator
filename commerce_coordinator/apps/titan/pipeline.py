"""
Pipelines for Titan
"""

import logging

from openedx_filters import PipelineStep
from requests import HTTPError
from rest_framework.exceptions import APIException

from commerce_coordinator.apps.titan.clients import TitanAPIClient
from commerce_coordinator.apps.titan.exceptions import NoActiveOrder, PaymentNotFound
from commerce_coordinator.apps.titan.serializers import PaymentSerializer, TitanActiveOrderSerializer

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

    def run_filter(self, edx_lms_user_id, payment_number=None, **kwargs):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Args:
            edx_lms_user_id: The edx.org LMS user ID of the user receiving the order.
            payment_number: Optional. The Payment identifier in Spree.

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
        payment_serializer = PaymentSerializer(data=payment)
        payment_serializer.is_valid(raise_exception=True)
        return payment_serializer.data


class CreateDraftPayment(PipelineStep):
    """
    Creates and Adds Titan's payment in payment data list.
    """

    def run_filter(
        self,
        order_uuid,
        response_code,
        payment_method_name,
        provider_response_body,
    ):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Args:
            Args:
            order_uuid(str): Order UUID related to this order.
            response_code(str): Payment attempt response code (payment intent id) provided by stripe.
            payment_method_name(str): The name of the payment method used for this payment. See enums for valid values.
            provider_response_body(str): The response JSON dump from a request to the payment provider.

        """

        api_client = TitanAPIClient()
        try:
            payment = api_client.create_payment(
                order_uuid=order_uuid,
                response_code=response_code,
                payment_method_name=payment_method_name,
                provider_response_body=provider_response_body,

            )
        except HTTPError as exc:
            logger.exception('[CreateTitanPayment] Failed to create pyment for order_uuid: %s', order_uuid)
            raise APIException("Error while creating payment on titan's system") from exc

        payment_serializer = PaymentSerializer(data=payment)
        payment_serializer.is_valid(raise_exception=True)
        return payment_serializer.data


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
        active_order_output = TitanActiveOrderSerializer(data=order)
        active_order_output.is_valid(raise_exception=True)

        recent_payment = None
        order_data = active_order_output.data
        payments = order_data['payments']
        if payments:
            recent_payment = payments[0]
        return {
            'order_data': order_data,
            'recent_payment': recent_payment
        }
