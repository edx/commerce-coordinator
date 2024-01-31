"""
Tests for Enterprise client.
"""

import ddt
import mock
from django.conf import settings
from django.test import TestCase, override_settings
from requests import Response

from commerce_coordinator.apps.enterprise_learner.enterprise_client import EnterpriseApiClient


@override_settings(
    BACKEND_SERVICE_EDX_OAUTH2_PROVIDER_URL='https://testserver.com/auth'
)
@ddt.ddt
class TestEnterpriseApiClient(TestCase):
    """
    Test Discovery Api client.
    """

    @ddt.data(
        {'username': "edx_enterprise",
         'response_data': {
             "count": 1,
             "num_pages": 1,
             "current_page": 1,
             "next": None,
             "start": 0,
             "previous": None,
             "results": [
                 {
                     "enterprise_customer": {
                         "uuid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                         "name": "edx",
                         "active": True
                     },
                     "user_id": 1,
                     "user": {
                         "username": "edx",
                         "first_name": "",
                         "last_name": "",
                         "email": "edx@example.com"
                     },
                     "data_sharing_consent_records": [
                         {
                             "username": "edx",
                             "enterprise_customer_uuid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
                         }
                     ]
                 }
             ]
         }
         },
        {
            'username': "edx_non_enterprise",
            'response_data': {
                "count": 0,
                "num_pages": 0,
                "current_page": 1,
                "next": None,
                "start": 0,
                "previous": None,
                "results": []
            }
        }
    )
    @ddt.unpack
    def test_check_user_is_enterprise_customer(self, username, response_data):
        """Successfully checks if user is enterprise"""
        with mock.patch('requests.Response.json') as mock_json:
            with mock.patch('commerce_coordinator.apps.core.clients.OAuthAPIClient') as mock_oauth_client:
                mock_json.return_value = response_data
                mock_oauth_client.return_value.get.return_value = Response()
                mock_oauth_client.return_value.get.return_value.status_code = 200

                client = EnterpriseApiClient()
                is_enterprise_customer = client.check_user_is_enterprise_customer(username)
                assert is_enterprise_customer == (response_data['count'] > 0)

                expected_url = (
                    f'{settings.LMS_URL_ROOT}/'
                    f'enterprise/api/v1/'
                    f'enterprise-learner'
                )

                # Check that the API endpoint was only called once.
                mock_oauth_client.return_value.get.assert_called_once_with(
                    expected_url,
                    timeout=settings.ENTERPRISE_CLIENT_TIMEOUT,
                    params={'username': username}
                )

    @ddt.data(
        {
            'username': 'edx_non_enterprise',
        }
    )
    @ddt.unpack
    def test_check_user_is_enterprise_customer_failure(self, username):
        with mock.patch('commerce_coordinator.apps.core.clients.OAuthAPIClient') as mock_oauth_client:
            mock_oauth_client.return_value.get.return_value = Response()
            mock_oauth_client.return_value.get.return_value.status_code = 400
            client = EnterpriseApiClient()
            mock_response = client.check_user_is_enterprise_customer(username)
            mock_response_msg = 'Not enterprise user'
            self.assertFalse(mock_response, mock_response_msg)
