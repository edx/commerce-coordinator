"""
API clients for LMS app.
"""
from celery.utils.log import get_task_logger
from django.conf import settings
from requests.exceptions import RequestException

from commerce_coordinator.apps.core.clients import BaseEdxOAuthClient, urljoin_directory
from commerce_coordinator.apps.lms.signals import fulfillment_completed_update_ct_line_item_signal

# Use special Celery logger for tasks client calls.
logger = get_task_logger(__name__)


class LMSAPIClient(BaseEdxOAuthClient):
    """
    API client for calls to the edX LMS service.
    """

    @property
    def api_enrollment_base_url(self):
        """
        Base URL for LMS Enrollment API service.
        """
        return urljoin_directory(
            settings.LMS_URL_ROOT, '/api/enrollment/v1/enrollment'
        )

    @property
    def api_entitlement_base_url(self):
        """
        Base URL for LMS Entitlement API service.
        """
        return urljoin_directory(
            settings.LMS_URL_ROOT, '/api/entitlements/v1/entitlements/'
        )

    @property
    def deactivate_user_api_url(self):
        """
        Base URL for LMS Deactivate User API service.
        """
        return urljoin_directory(
            settings.LMS_URL_ROOT, '/api/user/v1/accounts/{username}/deactivate/'
        )

    def deactivate_user(self, username, ct_message_id):
        """
        Call up the LMS to deactivate a user account.

        Intended use is on SDN check failure.
        """
        try:
            logger.info(
                f"[LMSAPIClient.deactivate_user] Initiating account deactivation on LMS for user '{username}', "
                f"triggered by CT subscription message ID: {ct_message_id}."
            )
            response = self.client.post(
                self.deactivate_user_api_url.format(username=username),
                timeout=self.normal_timeout,
            )
            response.raise_for_status()
        except (ConnectionError, RequestException) as exc:
            logger.error(
                f"[LMSAPIClient.deactivate_user] Failed to deactivate account for user '{username}', "
                f"(triggered by CT subscription Message ID: {ct_message_id}). Error: {exc}"
            )
            raise

    def enroll_user_in_course(
            self,
            enrollment_data,
            line_item_state_payload,
            fulfillment_logging_obj
    ):
        """
        Send a POST request to LMS Enrollment API endpoint.
        Arguments:
            enrollment_data: dictionary to send to the API resource.
        Returns:
            dict: Dictionary representation of JSON returned from API.
        """
        return self.post(
            fulfillment_type="enrollment",
            url=self.api_enrollment_base_url,
            json=enrollment_data,
            line_item_state_payload=line_item_state_payload,
            logging_obj=fulfillment_logging_obj,
            timeout=settings.FULFILLMENT_TIMEOUT
        )

    def entitle_user_to_course(
            self,
            entitlement_data,
            line_item_state_payload,
            fulfillment_logging_obj
    ):
        """
        Send a POST request to LMS Entitlement API endpoint.
        Arguments:
            entitlement_data: dictionary to send to the API resource.
        Returns:
            dict: Dictionary representation of JSON returned from API.
        """
        return self.post(
            fulfillment_type="entitlement",
            url=self.api_entitlement_base_url,
            json=entitlement_data,
            line_item_state_payload=line_item_state_payload,
            logging_obj=fulfillment_logging_obj,
            timeout=settings.FULFILLMENT_TIMEOUT
        )

    def post(
        self,
        fulfillment_type,
        url,
        json,
        line_item_state_payload,
        logging_obj,
        timeout=None,
    ):
        """
        Send a POST request to a URL with JSON payload.
        """
        if not timeout:   # pragma no cover
            timeout = self.normal_timeout
        try:
            headers = {
                # EDX_API_KEY is a legacy authentication mechanism. Even though
                # this endpoint uses OAuth2, we send a valid EDX_API_KEY
                # anyways because LMS still uses this key to recognize whether
                # a request should receive backend service superpowers.
                'X-Edx-Api-Key': settings.EDX_API_KEY
            }
            response = self.client.post(
                url,
                headers=headers,
                json=json,
                timeout=timeout,
            )
            response.raise_for_status()
            payload = {
                **line_item_state_payload,
                'is_fulfilled': True
            }
            logger.info(
                f"[LMSAPIClient.post.{fulfillment_type}] LMS fulfillment successful for user '{logging_obj['user']}'. "
                f"Details: lms_user_id: {logging_obj['lms_user_id']}, CT order ID: {logging_obj['order_id']}, "
                f"course ID: {logging_obj['course_id']}, CT subscription message ID: {logging_obj['message_id']}, "
                f"celery task ID: {logging_obj['celery_task_id']}."
            )

            response_json = response.json()

            if fulfillment_type == "entitlement":
                payload['entitlement_uuid'] = response_json.get('uuid')

            fulfillment_completed_update_ct_line_item_signal.send_robust(
                sender=self.__class__,
                **payload
            )

            return response_json
        except RequestException as exc:
            context_prefix = (
                f"[LMSAPIClient.post.{fulfillment_type}] lms_user_id:{logging_obj['lms_user_id']}, "
                f"CT order ID: {logging_obj['order_id']}"
                f"course ID: {logging_obj['course_id']}, celery task ID: {logging_obj['celery_task_id']}"
            )
            self.log_request_exception(context_prefix, logger, exc)

            payload = {
                **line_item_state_payload,
                'is_fulfilled': False
            }

            fulfillment_completed_update_ct_line_item_signal.send_robust(
                sender=self.__class__,
                **payload
            )
            raise
