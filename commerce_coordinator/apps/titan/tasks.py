"""
Titan Celery tasks
"""

from celery import shared_task
from celery.utils.log import get_task_logger

from .clients import TitanAPIClient, TitanOAuthAPIClient

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
    titan_api_client.post(
        '/enrollment-code-redemptions',
        {
            'source': 'edx',
            'productSku': sku,
            'couponCode': coupon_code,
            'edxLmsUserId': user_id,
            'edxLmsUserName': username,
            'email': email,
        }
    )


@shared_task()
def enrollment_code_redemption_requested_create_order_oauth_task(user_id, username, email, sku, coupon_code):
    """
    Ask to create an order to redeeem an enrollment code.

    Args:
        user_id: edX LMS user id redeeming enrollment code
        username: edX LMS username of user_id
        email: edX LMS user email of user_id
        sku: ecommerce partner_sku of product to redeem
        coupon_code: enrollment code
    """
    logger.info('Titan enrollment_code_redemption_requested_create_order_oauth_task fired '
                f'with user {user_id}, username {username}, email {email}, '
                f'sku {sku} and coupon code {coupon_code}.')

    titan_api_client = TitanOAuthAPIClient()
    titan_api_client.post(
        '/enrollment-code-redemptions',
        {
            'source': 'edx',
            'productSku': sku,
            'couponCode': coupon_code,
            'edxLmsUserId': user_id,
            'edxLmsUserName': username,
            'email': email,
        }
    )


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

    # Creating Cart/Basket
    order_created_response = titan_api_client.create_order(
        edx_lms_user_id, email, first_name, last_name
    )
    order_uuid = order_created_response['uuid']

    # Adding courses in Cart/Basket
    for sku in product_sku:
        titan_api_client.add_item(order_uuid, sku)

    # Completing Cart/Basket
    titan_api_client.complete_order(order_uuid, edx_lms_user_id)
