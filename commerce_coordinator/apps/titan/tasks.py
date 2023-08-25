"""
Titan Celery tasks
"""

from celery import shared_task
from celery.utils.log import get_task_logger
from requests import HTTPError

from commerce_coordinator.apps.core.cache import set_payment_paid_cache, set_payment_processing_cache
from commerce_coordinator.apps.core.constants import PaymentMethod, PaymentState
from commerce_coordinator.apps.stripe.clients import StripeAPIClient

from ..stripe.utils import sanitize_provider_response_body
from .clients import TitanAPIClient
from .filters import PaymentSuperseded
from .serializers import PaymentSerializer

logger = get_task_logger(__name__)


@shared_task()
def enrollment_code_redemption_requested_create_order_task(user_id, username, email, sku, coupon_code):
    """
    Ask to create an order to redeeem an enrollment code.

    Args:
        user_id: edX LMS user id redeeming enrollment code
        username: edX LMS username of user_id
        email: edX LMS user email of user_id
        sku: ecommerce partner_sku of product to redeem
        coupon_code: enrollment code
    """
    logger.info('Titan enrollment_code_redemption_requested_create_order_task fired '
                f'with user {user_id}, username {username}, email {email},'
                f'sku {sku} and coupon code {coupon_code}.')

    titan_api_client = TitanAPIClient()

    titan_api_client.redeem_enrollment_code(sku, coupon_code, user_id, username, email)


@shared_task()
def order_created_save_task(sku, edx_lms_user_id, email, coupon_code):
    """
    task to create a basket/order for a user in Titan.

    Args:
        sku: List. An edx.org stock keeping units (SKUs) that the user would like to purchase.
        edx_lms_user_id: The edx.org LMS user ID of the user receiving the order.
        email: The edx.org profile email of the user receiving the order. Required by Spree to create a user.
        coupon_code: A coupon code to initially apply to the order.

    Returns:
        order_id: Optional. The ID of the created order in Spree.
    """
    logger.info('Titan order_created_save_task fired '
                f'with user: {edx_lms_user_id}, email: {email},'
                f'sku: {sku} and coupon code: {coupon_code}.')

    titan_api_client = TitanAPIClient()

    titan_api_client.create_order(sku, edx_lms_user_id, email, coupon_code)


@shared_task()
def payment_processed_save_task(
    edx_lms_user_id, order_uuid, payment_number, payment_state, reference_number, amount_in_cents, currency,
    provider_response_body
):
    """
    task to update payment in Titan.

    Args:
        Args:
            edx_lms_user_id(int): The edx.org LMS user ID of the user making the payment.
            order_uuid (str): The identifier of the order. There should be only
                one Stripe PaymentIntent for this identifier.
            payment_number: The Payment identifier in Spree.
            payment_state: State to advance the payment to.
            reference_number: Payment attempt response code provided by stripe.
            amount_in_cents (int): The number of cents of the order.
            currency (str): ISO currency code. Must be Stripe-supported.
            provider_response_body: The saved response from a request to the payment provider.

    """
    logger.info('Titan payment_processed_save_task fired '
                f'with payment_number: {payment_number}, payment_state: {payment_state},'
                f'and response_code: {reference_number}.')

    titan_api_client = TitanAPIClient()

    try:
        payment = titan_api_client.update_payment(
            edx_lms_user_id=edx_lms_user_id,
            order_uuid=order_uuid,
            payment_number=payment_number,
            payment_state=payment_state,
            reference_number=reference_number,
            provider_response_body=provider_response_body,
        )
        payment_serializer = PaymentSerializer(data=payment)
        payment_serializer.is_valid()
        payment = payment_serializer.data

        # Set cache after successfully updating payment state in Titan's system.
        payment_state = payment['state']
        if payment_state == PaymentState.COMPLETED.value:
            set_payment_paid_cache(payment)
        elif payment_state == PaymentState.FAILED.value:
            stripe_api_client = StripeAPIClient()
            provider_response_body = stripe_api_client.retrieve_payment_intent(reference_number)
            provider_response_body = sanitize_provider_response_body(provider_response_body)
            new_payment = titan_api_client.create_payment(
                order_uuid=order_uuid,
                reference_number=reference_number,
                payment_method_name=PaymentMethod.STRIPE.value,
                provider_response_body=provider_response_body,
                edx_lms_user_id=edx_lms_user_id
            )
            new_payment_number = new_payment['number']
            PaymentSuperseded.run_filter(
                edx_lms_user_id=edx_lms_user_id,
                payment_intent_id=reference_number,
                order_uuid=order_uuid,
                payment_number=new_payment_number,
                amount_in_cents=amount_in_cents,
                currency=currency,
            )
            payment['new_payment_number'] = new_payment_number
            set_payment_processing_cache(payment)

    except HTTPError as ex:
        logger.exception('Titan payment_processed_save_task Failed '
                         f'with payment_number: {payment_number}, payment_state: {payment_state},'
                         f'and reference_number: {reference_number}. Exception: {ex}')
