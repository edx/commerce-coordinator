"""
Titan Celery tasks
"""

from celery import shared_task
from celery.utils.log import get_task_logger

from .clients import TitanAPIClient

# Use the special Celery logger for our tasks
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
def order_created_save_task(product_sku, edx_lms_user_id, email, first_name, last_name, coupon_code):
    """
    task to create a basket/order for a user in Titan.

    Args:
        product_sku: List. An edx.org stock keeping units (SKUs) that the user would like to purchase.
        edx_lms_user_id: The edx.org LMS user ID of the user receiving the order.
        email: The edx.org profile email of the user receiving the order. Required by Spree to create a user.
        first_name: The edx.org profile first name of the user receiving the order
        last_name: The edx.org profile last name of the user receiving the order
        coupon_code: A coupon code to initially apply to the order.

    Returns:
        order_id: Optional. The ID of the created order in Spree.
    """
    logger.info('Titan order_created_save_task fired '
                f'with user: {edx_lms_user_id}, email: {email},'
                f'sku: {product_sku} and coupon code: {coupon_code}.')

    titan_api_client = TitanAPIClient()

    titan_api_client.create_order(product_sku, edx_lms_user_id, email, first_name, last_name, coupon_code)


@shared_task()
def payment_processed_save_task(payment_number, payment_state, response_code):
    """
    task to update payment in Titan.

    Args:
        Args:
            payment_number: The Payment identifier in Spree.
            payment_state: State to advance the payment to.
            response_code: Payment attempt response code provided by stripe.

    """
    logger.info('Titan payment_processed_save_task fired '
                f'with payment_number: {payment_number}, payment_state: {payment_state},'
                f'and response_code: {response_code}.')

    titan_api_client = TitanAPIClient()

    titan_api_client.update_payment(
        payment_number=payment_number,
        payment_state=payment_state,
        response_code=response_code
    )
