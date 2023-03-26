"""
API clients for Titan.
"""
import requests
from celery.utils.log import get_task_logger
from django.conf import settings

from commerce_coordinator.apps.core.clients import Client

# Use special Celery logger for tasks client calls.
logger = get_task_logger(__name__)


class TitanAPIClient(Client):
    """
    API client for calls to Titan using API key.
    """

    def __init__(self):
        self.client = requests.Session()
        # Always send API key.
        self.client.headers.update(self.api_base_header)

    @property
    def api_base_url(self):
        """URL of API service."""
        return self.urljoin_directory(settings.TITAN_URL, '/edx/api/v1/')

    @property
    def api_base_header(self):
        """Header to add to all requests."""
        return {
            'Content-Type': 'application/vnd.api+json',
            'User-Agent': '',
            'X-Spree-API-Key': settings.TITAN_API_KEY,
        }

    def _request(self, request_method, resource_path, params=None, json=None, headers=None):
        """
        Send a request to a Titan API resource.

        Arguments:
            request_method: method for the new :class:`Request` object.
            resource_path: the path of the API resource
            params: (optional) Dictionary or bytes to be sent in the query string for the :class:`Request`.
            json: (optional) json to send in the body of the :class:`Request`.
            headers: (optional) Dictionary of HTTP Headers to send with the :class:`Request`.
        Returns:
            dict: Dictionary representation of JSON returned from API

        """
        try:
            resource_url = self.urljoin_directory(self.api_base_url, resource_path)
            response = self.client.request(
                method=request_method,
                url=resource_url,
                params=params,
                json=json,
                timeout=self.normal_timeout,
                headers=headers,
            )
            response.raise_for_status()
            response_json = response.json()
            logger.debug('Request URL: %s', response.request.url)
            logger.debug('Request method: %s', response.request.method)
            logger.debug('Request body: %s', response.request.body)
            logger.debug('Request headers: %s', response.request.headers)
            logger.debug('Response status: %s %s', response.status_code, response.reason)
            logger.debug('Response body: %s', response_json)
            return response_json
        except (requests.exceptions.HTTPError, requests.exceptions.JSONDecodeError) as exc:
            logger.error(exc)
            logger.info('Request URL: %s', exc.request.url)
            logger.info('Request method: %s', exc.request.method)
            logger.info('Request body: %s', exc.request.body)
            logger.debug('Request headers: %s', exc.request.headers)
            logger.info('Response status: %s %s', exc.response.status_code, exc.response.reason)
            logger.info('Response body: %s', exc.response.text)
            raise

    def create_order(self, edx_lms_user_id, email, first_name, last_name, currency='USD'):
        """
        Request Titan to create a basket/order for a user

        Args:
            edx_lms_user_id: The edx.org LMS user ID of the user receiving the order.
            email: The edx.org profile email of the user receiving the order. Required by Spree to create a user.
            first_name: The edx.org profile first name of the user receiving the order
            last_name: The edx.org profile last name of the user receiving the order
            currency: Optional. The ISO code of the currency to use for the order (defaults to USD)
        """
        return self._request(
            request_method='POST',
            resource_path='cart',
            json={
                'data': {
                    'attributes': {
                        'currency': currency,
                        'edxLmsUserId': edx_lms_user_id,
                        'email': email,
                        'firstName': first_name,
                        'lastName': last_name,
                    }
                }
            },
        )

    def add_item(self, order_uuid, course_sku):
        """
        Request Titan to add an item to a cart for a user

        Args:
            order_uuid: The UUID of the created order in Spree.
            course_sku: The SKU of the course being added to the order
        """
        return self._request(
            request_method='POST',
            resource_path='cart/add_item',
            json={
                'data': {
                    'attributes': {
                        'orderUuid': order_uuid,
                        'courseSku': course_sku,
                        }
                    }
                },
        )

    def complete_order(self, order_uuid, edx_lms_user_id):
        """
        Request Titan to complete the order

        Args:
            order_uuid: The UUID of the created order in Spree.
            edx_lms_user_id: The edx.org LMS user ID of the user receiving the order.
        """
        return self._request(
            request_method='POST',
            resource_path='checkout/complete',
            json={
                'orderUuid': order_uuid,
                'edxLmsUserId': edx_lms_user_id,
            },
        )

    def redeem_enrollment_code(self, sku, coupon_code, user_id, username, email):
        """
        Request Titan to redeem an enrollment code

        Args:
            sku: An edx.org stock keeping unit (SKUs) that the user would like to redeem.
            coupon_code: A coupon code that the user would like to use to redeem the sku.
            user_id: The LMS user id of the redeeming user.
            username: The LMS username of the redeeming user.
            email: The email of the redeeming user.
        """
        return self._request(
            request_method='POST',
            resource_path='redeem-enrollment-code',
            json={
                'source': 'edx',
                'productSku': sku,
                'couponCode': coupon_code,
                'edxLmsUserId': user_id,
                'edxLmsUserName': username,
                'email': email,
            },
        )
