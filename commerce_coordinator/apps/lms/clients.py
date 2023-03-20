"""
API clients for LMS app.
"""
import requests
from celery.utils.log import get_task_logger
from django.conf import settings

from commerce_coordinator.apps.core.clients import BaseEdxOAuthClient

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
        return self.urljoin_directory(settings.LMS_URL_ROOT, '/api/enrollment/v1/enrollment')


    def post(self, path, enrollment_data):
        """
        Send a POST request to LMS Enrollment API endpoint
        Arguments:
            enrollment_data: dictionary to send to the API resource.
        Returns:
            dict: Dictionary represention of JSON returned from API
        """
        try:
            enrollment_api_url = urljoin(self.api_enrollment_base_url, path)
            response = self.client.post(
                enrollment_api_url,
                json=enrollment_data,
                timeout=self.normal_timeout,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as exc:
            logger.error(exc)
            raise