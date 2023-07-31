"""
API clients for Titan.
"""
from celery.utils.log import get_task_logger
from django.conf import settings
from requests import Session
from requests.exceptions import RequestException

from commerce_coordinator.apps.core.clients import Client, urljoin_directory

# Use special Celery logger for tasks client calls.
logger = get_task_logger(__name__)


class TitanAPIClient(Client):
    """
    API client for calls to Titan using API key.
    """

    def __init__(self):
        self.client = Session()
        # Always send API key.
        self.client.headers.update(self.api_base_header)

    @property
    def api_base_url(self):
        """URL of API service."""
        return urljoin_directory(settings.TITAN_URL, '/edx/api/v1/')

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
            resource_url = urljoin_directory(self.api_base_url, resource_path)
            response = self.client.request(
                method=request_method,
                url=resource_url,
                params=params,
                json=json,
                timeout=self.normal_timeout,
                headers=headers,
            )
            response.raise_for_status()
            self.log_request_response(logger, response)
        except RequestException as exc:
            self.log_request_exception(logger, exc)
            raise
        return response.json()

    def create_order(self, sku, edx_lms_user_id, email, coupon_code, currency='USD'):
        """
        Task to create a basket/order for a user in Titan.

        Args:
            sku: List. An edx.org stock keeping units (SKUs) that the user would like to purchase.
            edx_lms_user_id: The edx.org LMS user ID of the user receiving the order.
            email: The edx.org profile email of the user receiving the order. Required by Spree to create a user.
            coupon_code: A coupon code to initially apply to the order.
            currency (str): Optional; The ISO code of the currency to use for the order (defaults to USD)

        Returns:
            order_id: Optional. The ID of the created order in Spree.
        """
        logger.info(f'TitanAPIClient.create_cart called '
                    f'with user: {edx_lms_user_id}, email: {email},'
                    f'sku: {sku} and coupon code: {coupon_code}.')

        # Creating Order (for Cart/Basket)
        order_created_response = self.create_cart(
            edx_lms_user_id, email, currency
        )
        order_uuid = order_created_response['data']['attributes']['uuid']

        # Adding courses in Cart/Basket
        for a_sku in sku:
            self.add_item(order_uuid, a_sku, edx_lms_user_id)

        return order_uuid

    def create_cart(self, edx_lms_user_id, email, currency='USD'):
        """
        Request Titan to create a basket/cart for a user

        Args:
            edx_lms_user_id: The edx.org LMS user ID of the user receiving the order.
            email: The edx.org profile email of the user receiving the order. Required by Spree to create a user.
            currency: Optional; The ISO code of the currency to use for the order (defaults to USD)
        """
        logger.info(f'TitanAPIClient.create_cart called using {locals()}.')
        return self._request(
            request_method='POST',
            resource_path='cart',
            json={
                'data': {
                    'attributes': {
                        'currency': currency,
                        'edxLmsUserId': edx_lms_user_id,
                        'email': email,
                    }
                }
            },
        )

    def add_item(self, order_uuid, course_sku, edx_lms_user_id):
        """
        Request Titan to add an item to a cart for a user

        Args:
            order_uuid: The UUID of the created order in Spree.
            course_sku: The SKU of the course being added to the order
        """
        logger.info(f'TitanAPIClient.add_item called using {locals()}.')
        return self._request(
            request_method='POST',
            resource_path='cart/add_item',
            json={
                'data': {
                    'attributes': {
                        'orderUuid': order_uuid,
                        'courseSku': course_sku,
                        'edxLmsUserId': edx_lms_user_id
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
        logger.info(f'TitanAPIClient.complete_order called using {locals()}.')
        return self._request(
            request_method='POST',
            resource_path='checkout/complete',
            json={
                'data': {
                    'attributes': {
                        'orderUuid': order_uuid,
                        'edxLmsUserId': edx_lms_user_id,
                    }
                }
            },
        )

    def get_active_order(self, edx_lms_user_id):
        """
        Request Titan for the user's current open order

        Args:
            edx_lms_user_id: the edx.org LMS user ID of the user receiving the order
        """

        logger.info(f'TitanAPIClient.get_active_order called using {locals()}.')
        response = self._request(
            request_method='GET',
            resource_path=f'accounts/{edx_lms_user_id}/active_order'
        )
        return response['data']['attributes']

    def get_payment(self, edx_lms_user_id=None, payment_number=None):
        """
        Request Titan to get payment details.

        Args:
            edx_lms_user_id: The edx.org LMS user ID of the user receiving the order.
            payment_number: The Payment identifier in Spree.
        """
        if payment_number is None and edx_lms_user_id is None:
            raise RuntimeError("payment_number or edx_lms_user_id should be passed as param.")

        query_params = {}
        if edx_lms_user_id is not None:
            query_params['edxLmsUserId'] = edx_lms_user_id
        if payment_number is not None:
            query_params['paymentNumber'] = payment_number

        logger.info(f'TitanAPIClient.get_payment called using {locals()}.')
        response = self._request(
            request_method='GET',
            resource_path='payments',
            params=query_params,
        )

        return response['data']['attributes']

    def update_payment(self, payment_number, payment_state, response_code):
        """
        Request Titan to update payment.

        Args:
            payment_number: The Payment identifier in Spree.
            payment_state: State to advance the payment to.
            response_code: Payment attempt response code provided by stripe.
        """
        response = self._request(
            request_method='PATCH',
            resource_path='payments',
            json={
                'data': {
                    'attributes': {
                        'paymentNumber': payment_number,
                        'paymentState': payment_state,
                        'responseCode': response_code,
                    }
                }
            },
        )

        return response['data']['attributes']

    def create_payment(
        self,
        order_uuid,
        response_code,
        payment_method_name,
        provider_response_body,
        edx_lms_user_id,
        reference=None,
        amount=None,
        payment_date=None,
        source=None,
    ):
        """
        Request Titan to Create payment.

        Args:
            order_uuid(str): Order UUID related to this order.
            response_code(str): Payment attempt response code (payment intent id) provided by stripe.
            payment_method_name(str): The name of the payment method used for this payment. See enums for valid values.
            provider_response_body(str): The response JSON dump from a request to the payment provider..
            reference(str): Optional. Reference to be saved against the payment.
            amount(float): Optional. Payment amount to apply to order.
            payment_date(ISO-8601 str): Optional. Payment date to save against the payment.
            source(dict): Optional. Payment source details to be saved. It should have 'ccType',
                'gatewayCustomerProfileId', 'gatewayPaymentProfileId', 'lastDigits', 'month', 'name' and 'year'
                keys in 'str' format.
        """
        payload_attributes = {
            'orderUuid': order_uuid,
            'responseCode': response_code,
            'paymentMethodName': payment_method_name,
            'providerResponseBody': provider_response_body,
            'edxLmsUserId': edx_lms_user_id,
        }
        if reference is not None:
            payload_attributes['reference'] = reference
        if amount is not None:
            payload_attributes['amount'] = amount
        if payment_date is not None:
            payload_attributes['paymentDate'] = payment_date
        if source is not None:
            payload_attributes['source'] = source

        response = self._request(
            request_method='POST',
            resource_path='payments',
            json={
                'data': {
                    'attributes': payload_attributes
                }
            },
        )

        return response['data']['attributes']

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

    def update_billing_address(self,
                               order_uuid,
                               address_1=None,
                               address_2=None,
                               city=None,
                               company=None,
                               country_iso=None,
                               first_name=None,
                               last_name=None,
                               phone=None,
                               state_name=None,
                               zipcode=None):
        """
        Request Titan to update the billing address for an order

        Args:
            order_uuid (str): UUID of the order associated to the billing address being updated
            address_1 (str): Optional: First address line of the billing address
            address_2 (str): Optional: Second address line of the billing address
            city (str): Optional: City name of the billing address
            company (str): Optional: Company name of the billing address
            country_iso (str): Optional: ISO code of the billing address's country
            first_name (str): Optional: First name of the person at the billing address
            last_name (str): Optional: Last name of the person at the billing address
            phone (str): Optional: Phone number of the billing address
            state_name (str): Optional: Name of the billing address's state
            zipcode (str): Optional: Zipcode of the billing address
        """
        payload_attributes = {
            'orderUuid': order_uuid,
        }
        if address_1 is not None:
            payload_attributes['address1'] = address_1
        if address_2 is not None:
            payload_attributes['address2'] = address_2
        if city is not None:
            payload_attributes['city'] = city
        if company is not None:
            payload_attributes['company'] = company
        if country_iso is not None:
            payload_attributes['countryIso'] = country_iso
        if first_name is not None:
            payload_attributes['firstName'] = first_name
        if last_name is not None:
            payload_attributes['lastName'] = last_name
        if phone is not None:
            payload_attributes['phone'] = phone
        if state_name is not None:
            payload_attributes['stateName'] = state_name
        if zipcode is not None:
            payload_attributes['zipcode'] = zipcode

        response = self._request(
            request_method='PATCH',
            resource_path='checkout/update_billing_address',
            json={
                'data': {
                    'attributes': payload_attributes,
                }
            },
        )

        return response['data']['attributes']
