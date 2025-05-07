"""
API client for communication with the Order Fulfillment service.
"""
import time

from celery.utils.log import get_task_logger
from django.conf import settings
from requests.exceptions import RequestException

from commerce_coordinator.apps.core.clients import BaseEdxOAuthClient, urljoin_directory

logger = get_task_logger(__name__)


class OrderFulfillmentAPIClient(BaseEdxOAuthClient):
    """
    API client for making requests to the edX Order Fulfillment service.
    """

    ORDER_FULFILLMENT_SERVICE_TIMEOUT = 5  # seconds

    @property
    def api_order_fulfillment_post_base_url(self):
        """
        Returns the base URL for the Order Fulfillment POST API endpoint.
        """
        return urljoin_directory(
            settings.ORDER_FULFILLMENT_URL_ROOT, '/api/fulfill-order/'
        )

    def fulfill_order(self, payload, logging_data):
        """
        Sends a fulfillment request to the Order Fulfillment service.

        Args:
            payload (dict): JSON payload with order details.
            logging_data (dict): Contextual information for logging.

        Returns:
            dict: JSON response from the fulfillment service.
        """

        return self.post(
            url=self.api_order_fulfillment_post_base_url,
            payload=payload,
            log_context=logging_data,
            timeout=self.ORDER_FULFILLMENT_SERVICE_TIMEOUT,
        )

    def post(self, url, payload, log_context, timeout=None, total_retries=3, base_backoff=None):
        """
        Sends a POST request to the fulfillment service.

        Args:
            url (str): The target URL.
            payload (dict): JSON payload to send.
            log_context (dict): Structured logging context.
            timeout (int, optional): Timeout in seconds. Defaults to normal_timeout.

        Returns:
            dict: JSON response from the service.

        Raises:
            RequestException: If fail.
        """
        if not timeout:
            timeout = self.normal_timeout

        headers = {
            'X-Edx-Api-Key': settings.EDX_API_KEY,
            'Content-Type': 'application/json',
        }

        def attempt(attempt_number):
            try:
                response = self.client.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=timeout,
                )
                response.raise_for_status()

                logger.info(
                    "[OrderFulfillmentAPIClient] Fulfillment request succeeded | %s",
                    log_context
                )
                return response.json()

            except RequestException as err:
                if attempt_number >= total_retries:
                    context_str = (
                        f"[OrderFulfillmentAPIClient] Fulfillment request failed "
                        f"URL: {url} | Error: {err} | {log_context}"
                    )
                    self.log_request_exception(context_str, logger, err)
                    return None  # since we have already retried, we dont want to retry task by raising exception here

                next_attempt = attempt_number + 1
                next_backoff = base_backoff * next_attempt
                logger.warning(
                    "[OrderFulfillmentAPIClient] Fulfillment request failed for URL: %s with error: %s. %s"
                    "Retrying attempt #%s in %s seconds...",
                    url, err, log_context, next_attempt, next_backoff
                )
                time.sleep(next_backoff)
                return attempt(next_attempt)

        return attempt(0)

