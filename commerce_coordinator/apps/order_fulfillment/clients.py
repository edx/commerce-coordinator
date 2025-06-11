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
        Returns the base URL for OF fulfill-order POST API endpoint.
        """
        return urljoin_directory(
            settings.ORDER_FULFILLMENT_URL_ROOT, '/api/fulfill-order/'
        )

    @property
    def api_order_fulfillment_revoke_line_post_base_url(self):
        """
        Returns the base URL for OF revoke-line POST API endpoint.
        """
        return urljoin_directory(
            settings.ORDER_FULFILLMENT_URL_ROOT, '/api/revoke-line/'
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
            request_usage='Fulfillment',
            timeout=self.ORDER_FULFILLMENT_SERVICE_TIMEOUT,
        )

    def revoke_line(self, payload, logging_data):
        """
        Sends a POST request to the Order Fulfillment service to revoke course line Item for mobile orders.

        Args:
            payload (dict): JSON payload with order details.
            logging_data (dict): Contextual information for logging.

        Returns:
            dict: JSON response from the fulfillment service.
        """

        return self.post(
            url=self.api_order_fulfillment_revoke_line_post_base_url,
            payload=payload,
            log_context=logging_data,
            request_usage='Revoke Line',
            timeout=self.ORDER_FULFILLMENT_SERVICE_TIMEOUT,
        )

    def post(
        self,
        url: str,
        payload: dict,
        log_context: dict,
        request_usage: str,
        timeout: int = None,
        total_retries: int = 3,
        base_backoff: int = 1,
    ) -> dict | None:
        """
        Sends a POST request to the Order Fulfillment service with retry logic.

        Args:
            url (str): The endpoint to which the request is sent.
            payload (dict): The JSON body of the POST request.
            log_context (dict): Context for structured logging (e.g., user, order ID).
            request_usage (str): A description of what the request is used for (e.g., "Fulfillment" or "Revoke Line").
            timeout (int, optional): Timeout in seconds for the request. Defaults to self.normal_timeout.
            total_retries (int): Number of retry attempts on failure. Defaults to 3.
            base_backoff (int): Base backoff time in seconds, increasing linearly with each attempt. Defaults to 1.

        Returns:
            dict | None: The response from the fulfillment service as a JSON dict if successful, otherwise None.

        Notes:
            This method logs structured messages and retries with linear backoff. After exhausting retries,
            it logs the error and returns None instead of raising, so calling tasks must handle this gracefully.
        """
        timeout = timeout or self.normal_timeout

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
                    f"[OrderFulfillmentAPIClient] {request_usage} request succeeded | {log_context}",
                )
                return response.json()

            except RequestException as err:
                if attempt_number >= total_retries:
                    context_str = (
                        f"[OrderFulfillmentAPIClient] {request_usage} request failed "
                        f"after {total_retries} attempts. URL: {url} | Error: {err} | {log_context}"
                    )
                    self.log_request_exception(context_str, logger, err)
                    return None  # since we have already retried, we dont want to retry task by raising exception here

                next_attempt = attempt_number + 1
                next_backoff = base_backoff * next_attempt
                logger.warning(
                    f"[OrderFulfillmentAPIClient] {request_usage} request failed for URL: {url} "
                    f"with error: {err}. {log_context}"
                    f"Retrying attempt #{next_attempt} in {next_backoff} seconds...",
                )
                time.sleep(next_backoff)
                return attempt(next_attempt)

        return attempt(0)
