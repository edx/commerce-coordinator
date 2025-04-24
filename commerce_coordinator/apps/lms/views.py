"""
Views for the ecommerce app
"""
import datetime
import logging
import re
from typing import List
from urllib.parse import urlencode, urljoin

from commercetools import CommercetoolsError
from django.conf import settings
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from edx_rest_framework_extensions.permissions import LoginRedirectIfUnauthenticated
from openedx_filters.exceptions import OpenEdxFilterException
from requests import HTTPError
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_303_SEE_OTHER,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR
)
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient
from commerce_coordinator.apps.commercetools.http_api_client import CTCustomAPIClient
from commerce_coordinator.apps.core.constants import HttpHeadersNames, MediaTypes
from commerce_coordinator.apps.core.exceptions import InvalidFilterType
from commerce_coordinator.apps.lms.constants import CT_ABSOLUTE_DISCOUNT_TYPE
from commerce_coordinator.apps.lms.filters import (
    OrderRefundRequested,
    PaymentPageRedirectRequested,
    UserRetirementRequested
)
from commerce_coordinator.apps.lms.serializers import (
    CourseRefundInputSerializer,
    EntitlementRefundInputSerializer,
    FirstTimeDiscountInputSerializer,
    UserRetiredInputSerializer,
    enrollment_attribute_key
)
from commerce_coordinator.apps.lms.utils import get_order_line_item_info_from_entitlement_uuid, get_program_offer
from commerce_coordinator.apps.rollout.utils import is_legacy_order

logger = logging.getLogger(__name__)


class PaymentPageRedirectView(APIView):
    """Accept incoming request for routing users to the checkout view."""
    permission_classes = (LoginRedirectIfUnauthenticated,)
    throttle_classes = (UserRateThrottle,)

    def get(self, request):
        """
        Routes learners to desired checkout view

        Args:
            request (django.http.HttpRequest): django.http.HttpRequest

        Returns:
            an HTTP Response, in the form of an error or as an HTTP Redirect.

            - HTTP Redirect (303): Redirection to correct checkout page upon Success
            - HTTP File or Server Error (400-599) see Errors section for more information.

        Errors:
            - 400: if required params are missing or not in supported format.
            - 401: if user is unauthorized.

        """
        logger.debug(f'{self.get.__qualname__} request object: {request.data}.')
        logger.debug(f'{self.get.__qualname__} headers: {request.headers}.')

        try:
            user = request.user
            user.add_lms_user_id("PaymentPageRedirectView GET method")
            logger.info(
                f"Received request to redirect user having lms_user_id: {user.lms_user_id} to checkout"
                f" with query params: {list(self.request.GET.lists())}"
            )
            return self._redirect_response_payment(request)
        except OpenEdxFilterException as e:
            logger.exception(f"Something went wrong! Exception raised in {self.get.__name__} with error {repr(e)}")
            return HttpResponseBadRequest('Something went wrong.')

    def _redirect_response_payment(self, request):
        """
        Redirect to desired checkout view

        Args:
            request (django.http.HttpRequest):
        Returns:
            response (django.http.HttpResponseRedirect):
        """

        get_items = list(self.request.GET.lists())
        redirect_url_obj = PaymentPageRedirectRequested.run_filter(request)
        redirect_url = self._add_query_params_to_redirect_url(
            redirect_url_obj["redirect_url"], get_items
        )
        redirect = HttpResponseRedirect(redirect_url, status=HTTP_303_SEE_OTHER)
        redirect.headers[HttpHeadersNames.CONTENT_TYPE.value] = MediaTypes.JSON.value
        logger.debug(
            f"{self._redirect_response_payment.__qualname__} Redirecting 303 via {redirect}."
        )
        return redirect

    @staticmethod
    def _add_query_params_to_redirect_url(url, params):
        """
        Add query params to the URL for the MFE to use in its reporting
        Args:
            params (list): Query Params from Req as an encoded list
        Returns:
            url (str): A URL asa Python String
        """

        query_params = params
        query_params = urlencode(query_params, doseq=True)
        url = url + '?' + query_params if query_params else url

        return url


class OrderDetailsRedirectView(APIView):
    """Accept incoming request from the support tools MFE for routing staff users to the order details admin page."""
    permission_classes = [IsAdminUser]
    throttle_classes = (UserRateThrottle,)

    def get(self, request):
        """
        Routes staff to desired order details admin view.

        Args:
            request (django.http.HttpRequest): django.http.HttpRequest

        Returns:
            - HTTP Redirect (303): Redirection to correct checkout page upon Success

        Errors:
            - 400: if required params are missing or not in supported format.
            - 401: if user is unauthorized.

        """
        logger.info(f"{self.get.__qualname__} request object: {request.data}.")

        params = dict(request.GET.items())
        if not params.get('order_number', None):
            return HttpResponseBadRequest('Invalid order number supplied.')

        redirect_url = self._get_redirect_url(params)

        logger.info(f"[OrderDetailsRedirectView] - Redirecting 303 via {redirect_url}")

        return HttpResponseRedirect(redirect_url, status=HTTP_303_SEE_OTHER)

    @staticmethod
    def _get_redirect_url(params):
        """
        Construct order details page URL based on the e-commerce source system.
        Args:
            params (dict): Query params from request as a dictionary
        Returns:
            url (str): A URL as a Python String
        """
        order_number = params.get('order_number')

        logger.info(f"[OrderDetailsRedirectView] - Determining redirect url for order with number {order_number}")

        if is_legacy_order(order_number):
            url = urljoin(settings.ECOMMERCE_URL, f'{settings.ECOMMERCE_ORDER_DETAILS_DASHBOARD_PATH}{order_number}')
        else:
            ct_query_params = {
                'mode': 'basic',
                'searchMode': 'orderNumber',
                'searchTerm': f'{order_number}'
            }
            query_params = urlencode(ct_query_params, True)
            url = f'{settings.COMMERCETOOLS_MERCHANT_CENTER_ORDERS_PAGE_URL}?{query_params}'

        return url


class RefundView(APIView):
    """Accept incoming LMS request to process Refunds in Stripe."""
    permission_classes = [IsAdminUser]
    throttle_classes = (UserRateThrottle,)

    def post(self, request) -> Response:
        """
         Process a refund request from the LMS.

         Args:
             request (Request): The HTTP request object containing the refund details.

         Returns:
             - Response:
                 - 200 OK if the refund was successfully processed with the result of the OrderRefundRequested
                   filter/pipeline.
                 - 400 If the refund request failed due to an invalid order.
                 - 500 If an OpenEdxFilterException occurred while processing the refund.
                 - 500 If any other unexpected exception occurred during refund processing.

         The method expects a POST request with a JSON payload containing:
             - course_id (str): The ID of the course to refund.
             - username (str): The username of the user to refund.
             - enrollment_attributes (list): a `list` of `dict` related to the order and order line.

         The refund is processed by running the OrderRefundRequested filter/pipeline
         using the provided order_id and line_item_id extracted from the enrollment
         attributes.

         If the refund is successfully marked in CT, a 200 OK response is returned along
         with the result from the OrderRefundRequested filter/pipeline.

         If the refund fails due to a bad pipeline response, a 400 Bad Request is returned.

         If an exception occurs during refund processing, a 500 Internal Server Error
         is returned.
         """
        # pylint: disable=too-many-statements

        input_data = {**request.data}

        logger.info(f"{self.post.__qualname__} request object: {input_data}.")
        entitlement_refund = bool(input_data.get('entitlement_uuid'))
        if entitlement_refund:
            input_details = EntitlementRefundInputSerializer(data=input_data)

            try:
                input_details.is_valid(raise_exception=True)
            except ValidationError as e:
                logger.exception(f"[RefundView] Exception raised validating entitlement refund input "
                                 f"{self.post.__name__} with error {repr(e)}, input: {input_data}.")
                return Response('Invalid input provided', status=HTTP_400_BAD_REQUEST)

            username = input_details.data['username']
            order_number = input_details.data.get('order_number')
            entitlement_uuid = input_details.data.get('entitlement_uuid')
            logger.info(f"[RefundView] Starting LMS Refund of Entitlement for username: {username}, "
                        f"order_number: {order_number}, Entitlement UUID: {entitlement_uuid}.")

            try:
                order_id, order_line_item_id = get_order_line_item_info_from_entitlement_uuid(
                    order_number, entitlement_uuid)
            except CommercetoolsError as err:  # pragma no cover
                logger.exception(f"[RefundView] Commercetools Error: {err}, {err.errors}")
                return Response('Error while fetching order', status=HTTP_500_INTERNAL_SERVER_ERROR)

        else:
            input_details = CourseRefundInputSerializer(data=input_data)
            try:
                input_details.is_valid(raise_exception=True)
            except ValidationError as e:
                logger.exception(f"[RefundView] Exception raised validating course refund  input "
                                 f"{self.post.__name__} with error {repr(e)}, input: {input_data}.")
                return Response('Invalid input provided', status=HTTP_400_BAD_REQUEST)

            course_id = input_details.data['course_id']
            username = input_details.data['username']

            enrollment_attributes = input_details.enrollment_attributes_dict()

            logger.info(f"[RefundView] Starting LMS Refund for username: {username}, course_id: {course_id}, "
                        f"Enrollment attributes: {enrollment_attributes}.")

            order_line_item_id = enrollment_attributes.get(enrollment_attribute_key('order', 'line_item_id'), None)
            order_id = enrollment_attributes.get(enrollment_attribute_key('order', 'order_id'), None)

        if not order_id:
            logger.error(f"[RefundView] Failed processing refund for username: {username}, "
                         f"course_id: {course_id} the enrollment_attributes array requires an orders: order_id "
                         f"attribute.")
            return Response('the enrollment_attributes array requires an orders: order_id '
                            'attribute.', status=HTTP_400_BAD_REQUEST)

        if not order_line_item_id:
            log_msg = (
                f"[RefundView] Failed processing refund for order {order_id} for username: {username}, "
                f"entitlement_uuid: {entitlement_uuid}. Line item does not exist in commercetools Order."
            ) if entitlement_refund else (
                f"[RefundView] Failed processing refund for order {order_id} for username: {username}, "
                f"course_id: {course_id} the enrollment_attributes array requires an orders: line_item_id "
                f"attribute."
            )
            logger.error(log_msg)

            response_msg = 'Line item does not exist.' if entitlement_refund else \
                'the enrollment_attributes array requires an orders: line_item_id attribute.'
            return Response(response_msg, status=HTTP_400_BAD_REQUEST)

        try:
            result = OrderRefundRequested.run_filter(order_id, order_line_item_id)

            log_type = f"{entitlement_uuid=}" if entitlement_refund else f"{course_id=}"
            if result.get('returned_order', None):
                logger.info(f"[RefundView] Successfully returned order {order_id} for username: {username}, "
                            f"{log_type} with result: {result}.")
                return Response(status=HTTP_200_OK)
            else:
                logger.error(f"[RefundView] Failed returning order {order_id} for username: {username}, "
                             f"{log_type} with invalid filter/pipeline result: {result}.")
                return Response('Exception occurred while returning order', status=HTTP_400_BAD_REQUEST)

        # Handle the case when refund already exist
        except InvalidFilterType as e:
            logger.info(f"{e.message}")
            return Response(e.message, status=HTTP_200_OK)
        except OpenEdxFilterException as e:
            logger.exception(f"[RefundView] Exception raised in {self.post.__name__} with error {repr(e)}")
            return Response('Exception occurred while returning order', status=HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:  # pylint: disable=broad-except
            logger.exception(f"[RefundView] Exception raised in {self.post.__name__} with error {repr(e)}")
            return Response('Exception occurred while returning order', status=HTTP_500_INTERNAL_SERVER_ERROR)


class RetirementView(APIView):
    """Accept incoming LMS request to retire user in CT."""
    permission_classes = [IsAdminUser]
    throttle_classes = (UserRateThrottle,)

    def post(self, request) -> Response:
        """
        Process a refund request from the LMS.

        Args:
            request (Request): The HTTP request object containing the refund details.

        Returns:
            - Response:
                - 200 OK if the refund was successfully processed with the result of
                    the UserRetirementRequested filter/pipeline.
                - 400 If the retirement request failed due to an invalid lms user uuid.
                - 500 If an OpenEdxFilterException occurred while anonymizing the customer fields.
                - 500 If any other unexpected exception occurred during retirement/anonymizing processing.

        The method expects a POST request with a JSON payload containing:
            - lms_user_is (str): The ID of the lms user.

        The user retirement/field anonymization is processed by running the UserRetirementRequested
        filter/pipeline using the provided lms_user_id from the request

        If the retirement is successfully marked in CT (the PII fields are successfully anonymized), a 200 OK
        response is returned along with the result from the UserRetirementRequested filter/pipeline.

        If the retirement fails due to a bad pipeline response, a 400 Bad Request is returned.

        If an exception occurs during retirement processing, a 500 Internal Server Error is returned.
        """
        input_data = {**request.data}

        input_details = UserRetiredInputSerializer(data=input_data)
        try:
            input_details.is_valid(raise_exception=True)
        except ValidationError as e:
            logger.exception(f"[RetirementView] Exception raised validating input {self.post.__name__} "
                             f"with error {repr(e)}, input: {input_data}.")
            return Response('Invalid input provided', status=HTTP_400_BAD_REQUEST)

        lms_user_id = input_details.data['edx_lms_user_id']

        try:
            result = UserRetirementRequested.run_filter(lms_user_id)

            if result.get('returned_customer', None):
                logger.info(f"[RetirementView] Successfully anonymized fields for retired customer with "
                            f"LMS ID {lms_user_id}, with result: {result}.")
                return Response(status=HTTP_200_OK)
            else:
                logger.error(f"[RetirementView] Failed anonymizing fields for retired customer with "
                             f"LMS ID {lms_user_id}, with invalid filter/pipeline result: {result}.")
                return Response('Exception occurred while returning order', status=HTTP_400_BAD_REQUEST)

        except OpenEdxFilterException as e:
            logger.exception(f"[RetirementView] Exception raised in {self.post.__name__} with error {repr(e)}")
            return Response('Exception occurred while retiring Commercetools customer',
                            status=HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:  # pylint: disable=broad-except
            logger.exception(f"[RefundView] Exception raised in {self.post.__name__} with error {repr(e)}")
            return Response('Exception occurred while retiring Commercetools customer',
                            status=HTTP_500_INTERNAL_SERVER_ERROR)


class FirstTimeDiscountEligibleView(APIView):
    """View to check if a user is eligible for a first time discount"""
    permission_classes = [IsAdminUser]
    throttle_classes = []

    def post(self, request):
        """Return True if user is eligible for a first time discount."""
        validator = FirstTimeDiscountInputSerializer(data=request.data)
        validator.is_valid(raise_exception=True)

        email = validator.validated_data['email']
        code = validator.validated_data['code']

        try:
            ct_api_client = CommercetoolsAPIClient()
            is_eligible = ct_api_client.is_first_time_discount_eligible(email, code)

            output = {
                'is_eligible': is_eligible
            }
            return Response(output)
        except CommercetoolsError as err:  # pragma no cover
            logger.exception(f"[FirstTimeDiscountEligibleView] Commercetools Error: {err}, {err.errors}")
        except HTTPError as err:  # pragma no cover
            logger.exception(f"[FirstTimeDiscountEligibleView] HTTP Error: {err}")

        return Response({'is_eligible': True})


class ProgramPriceView(APIView):
    """View to get the price of a program."""
    authentication_classes = (JwtAuthentication,)
    permission_classes = (IsAuthenticated,)
    throttle_classes = []

    def _calculate_discounted_price(self, program_offer: dict, program_price: float) -> float:
        """Calculate the discounted price of the program."""
        if not program_offer:
            return program_price

        discounted_price = program_price
        if program_offer.get("discount_type") == CT_ABSOLUTE_DISCOUNT_TYPE:
            discounted_price -= program_offer.get("discount_value_in_cents")
        else:
            discounted_price -= discounted_price * program_offer.get("discount_value_in_cents") / 10000

        if discounted_price < 0:
            return program_price

        return discounted_price

    def _extract_parent_course_key(self, course_key: str) -> str:
        """
        Extract course_id for comparision
        """
        match = re.search(r'course-v1:([^+]+)\+([^+]+)', course_key)
        if match:
            return f"{match.group(1)}+{match.group(2)}"
        else:
            return None

    def _extract_course_key_from_variant_key(self, variant_key: str) -> tuple:
        """
        Extract course key for comparision
        """
        match = re.match(r"([a-f0-9-]+|[a-zA-Z]+)\+(.+)", variant_key)
        course_key = match.group(2) if match else ""

        return course_key

    def _get_program_entitlements_to_be_purchased(
            self,
            program_variants: List[object],
            user_enrollable_course_keys: List[object],
    ) -> List[str]:
        """Filter out bundle entitlements based on enrollable conditions."""

        if not user_enrollable_course_keys:
            return [variant.get("entitlement_sku") for variant in program_variants]

        return [
            variant.get("entitlement_sku")
            for variant in program_variants
            if self._extract_course_key_from_variant_key(variant.get("variant_key", ""))
            in user_enrollable_course_keys
        ]

    def _cents_to_dollars(self, cent_amount: float) -> float:
        """Convert cent amount to dollar."""
        return cent_amount / 100

    def get(self, request, bundle_key=None):
        """Return the price of the bundle for the specified course."""
        user_purchasable_course_keys = request.GET.getlist("course_key")

        try:
            view_start_time = datetime.datetime.now()
            ct_api_client = CTCustomAPIClient()

            # Fetch bundle variants with entitlements
            start_time = datetime.datetime.now()
            ct_program_variants = ct_api_client.get_program_variants(bundle_key)
            duration = (datetime.datetime.now() - start_time).total_seconds()
            logger.info(
                f"[Performance Check - ProgramPriceView] - ct_program_variants took {duration} seconds. "
                f"Bundle key: {bundle_key}"
            )

            if not ct_program_variants:
                logger.error(f"[ProgramPriceView] No program variants found for the program: {bundle_key}.")
                return Response('Program variants not found.', status=HTTP_404_NOT_FOUND)

            start_time = datetime.datetime.now()
            ct_discount_offers = ct_api_client.get_ct_bundle_offers_without_code()
            duration = (datetime.datetime.now() - start_time).total_seconds()
            logger.info(
                f"[Performance Check - ProgramPriceView] - get_ct_bundle_offers_without_code took {duration} seconds. "
                f"Bundle key: {bundle_key}"
            )

            # Get applied program offer
            program_offer = get_program_offer(ct_discount_offers, bundle_key)

            # Calculate program price based on already filtered course keys passed from LMS
            purchasable_entitlements_skus = self._get_program_entitlements_to_be_purchased(
                ct_program_variants,
                user_purchasable_course_keys,
            )

            # Get price of each entitlement in the bundle
            start_time = datetime.datetime.now()
            entitlements_standalone_prices = ct_api_client.get_program_entitlements_standalone_prices(
                purchasable_entitlements_skus
            )
            duration = (datetime.datetime.now() - start_time).total_seconds()
            logger.info(
                f"[Performance Check - ProgramPriceView] - entitlements_standalone_prices took {duration} seconds. "
                f"Bundle key: {bundle_key}, purchasable_entitlements_skus: {purchasable_entitlements_skus}"
            )

            # Calculate total price of the bundle
            total_cent_amount = sum(item.get("value", {}).get("centAmount") for item in entitlements_standalone_prices)

            discounted_cent_amount = self._calculate_discounted_price(program_offer, total_cent_amount)
            currencyCode = (
                entitlements_standalone_prices[0].get("value").get("currencyCode")
                if entitlements_standalone_prices
                else ""
            )

            output = {
                "total_incl_tax_excl_discounts": self._cents_to_dollars(total_cent_amount),
                "total_incl_tax": self._cents_to_dollars(discounted_cent_amount),
                "currency": currencyCode,
            }
            view_duration = (datetime.datetime.now() - view_start_time).total_seconds()
            logger.info(
                f"[Performance Check - ProgramPriceView] - view execution took {view_duration} seconds. "
                f"Bundle key: {bundle_key}, output: {output}"
            )
            return Response(output, status=HTTP_200_OK)

        except HTTPError as err:
            logger.exception(f"[ProgramPriceView] HTTP Error: {err}")
            return Response('Error occurred while fetching data', status=HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as err:  # pylint: disable=broad-except
            logger.exception(f"[ProgramPriceView] Unexpected Error: {err}")
            return Response('Unexpected error occurred', status=HTTP_500_INTERNAL_SERVER_ERROR)
