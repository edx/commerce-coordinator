"""
Pipelines for Titan
"""

import logging

from openedx_filters import PipelineStep
from requests import HTTPError
from rest_framework.exceptions import APIException

from commerce_coordinator.apps.core.constants import PaymentState
from commerce_coordinator.apps.titan.clients import TitanAPIClient
from commerce_coordinator.apps.titan.exceptions import (
    AlreadyPaid,
    InvalidOrderPayment,
    NoActiveOrder,
    PaymentMismatch,
    PaymentNotFound,
    ProcessingAlreadyRequested
)
from commerce_coordinator.apps.titan.serializers import (
    BillingAddressSerializer,
    PaymentSerializer,
    TitanActiveOrderSerializer
)

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

        if order_data is None:
            order_data = {}

        order_data['order_uuid'] = titan_response['uuid']

        return {
            "order_data": order_data
        }


class GetTitanPayment(PipelineStep):
    """
    Adds Titan's payment in payment data list.
    """

    # pylint: disable=arguments-differ
    def run_filter(self, edx_lms_user_id, payment_number=None, order_uuid=None, **kwargs):
        """
        Pipe payment information from Titan.

        It also validates that information from Titan is for expected payment_number and order_uuid.

        Args:
            edx_lms_user_id: The edx.org LMS user ID of the user receiving the order.
            payment_number: Optional. Payment identifier in Spree. This is expected payment number from Titan.
            order_uuid: Optional. Order identifier in Spree. This is expected order UUID from Titan
        """

        api_client = TitanAPIClient()
        try:
            payment = api_client.get_payment(
                edx_lms_user_id=edx_lms_user_id,
            )
        except HTTPError as exc:
            logger.exception("[GetTitanPayment] Payment %s not found for user: %s", payment_number, edx_lms_user_id)
            raise PaymentNotFound from exc
        payment_serializer = PaymentSerializer(data=payment)
        payment_serializer.is_valid(raise_exception=True)
        payment = payment_serializer.data

        if order_uuid and order_uuid != payment['order_uuid']:
            raise InvalidOrderPayment(
                f'Requested order_uuid "{order_uuid}" does not match with '
                f'order_uuid "{payment["order_uuid"]}" in Spree system.'
            )

        if payment_number and payment_number != payment['payment_number']:
            raise PaymentMismatch(
                f'Requested payment number "{payment_number}" does not match with '
                f'payment number "{payment["payment_number"]}" in Spree system.'
            )

        return {
            'payment_data': payment
        }


class ValidatePaymentReadyForProcessing(PipelineStep):
    """
    Validate if Titan payment is in valid state for Ready for Processing.
    """

    def run_filter(self, payment_data, payment_number=None, **kwargs):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Args:
            payment_data: Titan payment data to validate.
            payment_number: Optional. The Payment identifier in Spree.
        """

        if payment_data['state'] == PaymentState.COMPLETED.value:
            raise AlreadyPaid(f'Requested payment "{payment_number}" for processing is already paid.')
        if payment_data['state'] == PaymentState.PENDING.value:
            raise ProcessingAlreadyRequested(
                f'Requested payment "{payment_number}" for processing is already processing.'
            )

        return {
            'payment_data': payment_data
        }


class CreateDraftPayment(PipelineStep):
    """
    Creates and Adds Titan's payment in payment data list.
    """

    def run_filter(
        self,
        order_uuid,
        payment_intent_id,
        client_secret,
        payment_method_name,
        provider_response_body,
        edx_lms_user_id,
    ):  # pylint: disable=arguments-differ
        """
        Execute a filter with the signature specified.
        Args:
            order_uuid(str): Order UUID related to this order.
            payment_method_name(str): The name of the payment method used for this payment. See enums for valid values.
            provider_response_body(str): The response JSON dump from a request to the payment provider.
            payment_intent_id(str): A Stripe Payment Intent ID (used to update payment intents)
            client_secret(str): A Stripe client secret string used by the UI to load the Stripe payment form.
            edx_lms_user_id(str): edX LMS User ID
        """

        api_client = TitanAPIClient()
        try:
            payment = api_client.create_payment(
                order_uuid=order_uuid,
                reference_number=payment_intent_id,
                payment_method_name=payment_method_name,
                provider_response_body=provider_response_body,
                edx_lms_user_id=edx_lms_user_id
            )
        except HTTPError as exc:
            logger.exception('[CreateTitanPayment] Failed to create payment for order_uuid: %s', order_uuid)
            raise APIException("Error while creating payment on titan's system") from exc

        payment['referenceNumber'] = client_secret

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


class UpdateBillingAddress(PipelineStep):
    """
    Updates the user's billing address info on an order in Titan
    """

    def run_filter(self, order_uuid, **kwargs):  # pylint: disable=arguments-differ

        api_client = TitanAPIClient()
        try:
            response = api_client.update_billing_address(order_uuid, **kwargs)

        except HTTPError as exc:
            logger.exception(
                "[UpdateBillingAddress] Failed to update the billing address for the specified order: %s",
                order_uuid
            )
            raise APIException("Error updating the order's billing address details in titan") from exc
        update_billing_address_output = BillingAddressSerializer(data=response)
        update_billing_address_output.is_valid(raise_exception=True)
        return {'billing_address_data': update_billing_address_output.data}


class UpdateTitanPayment(PipelineStep):
    """
    Updates a payment in Titan
    """

    def run_filter(
        self,
        edx_lms_user_id,
        order_uuid,
        payment_number,
        payment_state,
        payment_intent_id,
        **kwargs
    ):  # pylint: disable=arguments-differ

        api_client = TitanAPIClient()
        try:
            response = api_client.update_payment(
                edx_lms_user_id=edx_lms_user_id,
                order_uuid=order_uuid,
                payment_number=payment_number,
                payment_state=payment_state,
                reference_number=payment_intent_id
            )

        except HTTPError as exc:
            logger.exception(
                "[UpdateTitanPayment] Failed to update the payment information in Titan for the specified payment: %s",
                payment_number
            )
            raise APIException("Error updating the payment details in titan") from exc

        update_payment_output = PaymentSerializer(data=response)
        update_payment_output.is_valid(raise_exception=True)
        return {'payment_data': update_payment_output.data}
