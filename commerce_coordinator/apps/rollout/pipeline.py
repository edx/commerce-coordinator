import logging

from openedx_filters import PipelineStep
from openedx_filters.exceptions import OpenEdxFilterException
from requests import HTTPError

from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient
from commerce_coordinator.apps.commercetools_frontend.constants import COMMERCETOOLS_FRONTEND
from commerce_coordinator.apps.enterprise_learner.utils import is_user_enterprise_learner
from commerce_coordinator.apps.frontend_app_payment.constants import FRONTEND_APP_PAYMENT_CHECKOUT
from commerce_coordinator.apps.rollout.waffle import is_redirect_to_commercetools_enabled_for_user

logger = logging.getLogger(__name__)


class GetActiveOrderManagementSystem(PipelineStep):
    """
    Determines which order management system to redirect to, based on the existence of course_run_id
    and waffle flag's value.
    """

    def run_filter(self, request):
        """
        Execute a filter with the signature specified.
        Arguments:
            request: request object passed through from the lms filter
        Returns:
            dict:
                active_order_management_system: result from pipeline steps to determine if
                            redirect_to_commercetools_checkout flag is enabled and course_run_key
                            and sku query params exist and detect which checkout to redirect to
        """
        sku = request.query_params.get('sku', '').strip()
        course_run = request.query_params.get('course_run_key', '').strip()

        ct_api_client = CommercetoolsAPIClient()
        commercetools_available_course = None

        if course_run:
            try:
                commercetools_available_course = ct_api_client.get_product_variant_by_course_run(course_run)
            except HTTPError as exc:
                logger.exception(
                    f'[get_product_variant_by_course_run] Failed to get CT course '
                    f'for course_run: {course_run} with exception: {exc}'
                )

        if ((is_redirect_to_commercetools_enabled_for_user(request) and commercetools_available_course is not None)
                and not is_user_enterprise_learner(request)):
            active_order_management_system = COMMERCETOOLS_FRONTEND
        elif sku:
            active_order_management_system = FRONTEND_APP_PAYMENT_CHECKOUT
        else:
            logger.exception(f'An error occurred while determining the active order management system.'
                             f'No waffle flag, course_run_key or sku value found')
            raise OpenEdxFilterException(f'Neither course_run_key and waffle flag value nor sku found.'
                                         f'Unable to determine active order management system.')

        return {
            'active_order_management_system': active_order_management_system
        }
