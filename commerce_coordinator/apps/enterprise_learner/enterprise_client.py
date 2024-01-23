"""
API client for calls to Enterprise Service.
"""
import logging

from django.conf import settings
from requests.exceptions import ConnectionError, HTTPError, Timeout  # pylint: disable=redefined-builtin

from commerce_coordinator.apps.core.clients import BaseEdxOAuthClient

logger = logging.getLogger(__name__)


class EnterpriseApiClient(BaseEdxOAuthClient):
    """
    API client for calls to the Enterprise Service.
    """
    enterprise_api_base_url = f"{settings.ENTERPRISE_URL}/enterprise/api/v1"
    enterprise_customer_info_endpoint = f"{enterprise_api_base_url}/enterprise-learner"

    def check_user_is_enterprise_customer(self, username):
        """
        Checks if the user is an enterprise customer.
        Arguments:
            username (string): Username of the user
        Returns:
            is_enterprise_user (Boolean) : True if the user is an enterprise customer else False
        """
        try:
            response = self.client.get(self.enterprise_customer_info_endpoint,
                                       timeout=settings.ENTERPRISE_CLIENT_TIMEOUT,
                                       params={
                                           'username': username,
                                       })
            response.raise_for_status()
            response_json = response.json()
        except (ConnectionError, HTTPError, Timeout) as exc:
            logger.exception(f'An error occurred while requesting enterprise customer data'
                             f' from  {self.enterprise_customer_info_endpoint}: {exc}')
            return False

        response_data = response_json.get('count', 0)
        is_enterprise_user = response_data > 0

        return is_enterprise_user
