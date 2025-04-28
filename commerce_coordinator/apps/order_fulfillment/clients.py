"""
API Client for order fulfillment app
"""

from celery.utils.log import get_task_logger
from django.conf import settings

from commerce_coordinator.apps.commercetools.fulfillment_webhook_utils.webhook_caller import HMACWebhookCaller
from commerce_coordinator.apps.core.clients import BaseEdxOAuthClient, urljoin_directory

# Use special Celery logger for tasks client calls.
logger = get_task_logger(__name__)


class OrderFulfillmentAPIClient(BaseEdxOAuthClient):
    """
    API client for calls to the edX order fulfillment service.
    """

    @property
    def api_order_fulfillment_post_base_url(self):
        """
        Base URL for Order fulfillment POST API service.
        """
        return urljoin_directory(
            settings.ORDER_FULFILLMENT_URL_ROOT, '/core/fulfill_order'
        )

    def fulfill_order(
        self,
        payload
    ):
        """
        Sends a POST request to order fulfillment service for
        fulfillment of enrollment or entitlement via webhook

        """

        logger.info(f'WITHIN FULFILL ORDER WITH PYALOAD {payload}')

        HMACWebhookCaller().call(self.api_order_fulfillment_post_base_url, payload)
