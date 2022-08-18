"""
Titan Celery tasks
"""

from celery import shared_task
from celery.utils.log import get_task_logger

from .clients import TitanAPIClient, TitanOAuthAPIClient

# Use the special Celery logger for our tasks
logger = get_task_logger(__name__)


@shared_task()
def enrollment_code_redemption_requested_create_order_task(user_id, email, sku, coupon_code):
    """
    Ask to create an order to redeeem an enrollment code.

    Args:
        user_id: edX LMS user id redeeming enrollment code
        email: edX LMS user email of user_id
        sku: ecommerce partner_sku of product to redeem
        coupon_code: enrollment code
    """
    logger.info('Titan enrollment_code_redemption_requested_create_order_task fired '
                f'with user {user_id}, email {email}, sku {sku} and coupon code {coupon_code}.')

    titan_api_client = TitanAPIClient()
    titan_api_client.post(
        '/enrollment-code-redemptions',
        {
            'source': 'edx',
            'productSku': sku,
            'couponCode': coupon_code,
            'edxLmsUserId': user_id,
            'email': email,
        }
    )

@shared_task()
def enrollment_code_redemption_requested_create_order_oauth_task(user_id, email, sku, coupon_code):
    """
    Ask to create an order to redeeem an enrollment code.

    Args:
        user_id: edX LMS user id redeeming enrollment code
        email: edX LMS user email of user_id
        sku: ecommerce partner_sku of product to redeem
        coupon_code: enrollment code
    """
    logger.info('Titan enrollment_code_redemption_requested_create_order_oauth_task fired '
                f'with user {user_id}, email {email}, sku {sku} and coupon code {coupon_code}.')

    titan_api_client = TitanOAuthAPIClient()
    titan_api_client.post(
        '/enrollment-code-redemptions',
        {
            'source': 'edx',
            'productSku': sku,
            'couponCode': coupon_code,
            'edxLmsUserId': user_id,
            'email': email,
        }
    )
