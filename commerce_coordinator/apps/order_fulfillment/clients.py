from commerce_coordinator.apps.core.clients import BaseEdxOAuthClient, urljoin_directory
from django.conf import settings
from celery.utils.log import get_task_logger
from requests.exceptions import RequestException


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
            settings.ORDER_FULFILLMENT_URL_ROOT, '/api/enrollment/v1/enrollment'
        )
    

    def fulfill_order(
        self,
        payload,
        fulfillment_logging_obj
    ):
        """
        Sends a POST request to order fulfillment service for 
        fulfillment of enrollment or entitlement

        """
        return self.post(
            payload=payload,
            logging_obj=fulfillment_logging_obj,
            url=self.api_order_fulfillment_post_base_url
        )

    def post(
        self,
        payload,
        logging_obj,
        url
    ):
        """
        Send a POST request to a URL with JSON payload.
        """
        try:
            response = self.client.post(
                url,
                json=payload,
            )

            response.raise_for_status()
            
            logger.info(
                f"[OrderFulfillmentAPIClient.post] Order fulfillment successful for user '{logging_obj['user']}'. "
                f"Details: lms_user_id: {logging_obj['lms_user_id']}, CT order ID: {logging_obj['order_id']}, "
                f"course ID: {logging_obj['course_id']}, CT subscription message ID: {logging_obj['message_id']}, "
                f"celery task ID: {logging_obj['celery_task_id']}."
            )

            response_json = response.json()

            return response_json
        except RequestException as exc:
            context_prefix = (
                f"[OrderFulfillmentAPIClient.post] lms_user_id:{logging_obj['lms_user_id']}, "
                f"CT order ID: {logging_obj['order_id']}"
                f"course ID: {logging_obj['course_id']}, celery task ID: {logging_obj['celery_task_id']}"
            )
            self.log_request_exception(context_prefix, logger, exc)

            raise
