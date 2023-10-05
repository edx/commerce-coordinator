"""
API clients for commercetools app.
"""

import logging
from typing import Generic, List, Optional, TypeVar

from commercetools import Client as CTClient
from commercetools import CommercetoolsError
from commercetools.platform.models import Customer as CTCustomer
from commercetools.platform.models import CustomerSetCustomTypeAction, FieldContainer
from commercetools.platform.models import Order as CTOrder
from commercetools.platform.models import Type as CTType
from commercetools.platform.models import TypeDraft as CTTypeDraft
from commercetools.platform.models import TypeResourceIdentifier
from django.conf import settings

from commerce_coordinator.apps.commercetools.catalog_info.constants import EdXFieldNames
from commerce_coordinator.apps.commercetools.catalog_info.foundational_types import TwoUCustomTypes

logger = logging.getLogger(__name__)

T = TypeVar("T")


class PaginatedResult(Generic[T]):
    results: List[T]
    total: int
    offset: int

    def __init__(self, results: List[T], total: int, offset: int) -> None:
        super().__init__()
        self.results = results
        self.total = total
        self.offset = offset

    def next_offset(self) -> int:
        return self.offset + len(self.results)

    def has_more(self) -> bool:
        return (self.next_offset()) < self.total


class CommercetoolsAPIClient:  # (BaseEdxOAuthClient): ???
    base_client = None

    def __init__(self):
        super().__init__()
        config = settings.COMMERCETOOLS_CONFIG
        self.base_client = CTClient(
            client_id=config["clientId"],
            client_secret=config["clientSecret"],
            scope=[config["scopes"]],
            url=config["apiUrl"],
            token_url=config["authUrl"],
            project_key=config["projectKey"]
        )

    def ensure_custom_type_exists(self, type_def: CTTypeDraft) -> CTType:
        type_object = None
        type_exists = False
        try:
            type_object = self.base_client.types.get_by_key(type_def.key)
            type_exists = True
        except CommercetoolsError as _:
            # commercetools.exceptions.CommercetoolsError: The Resource with key 'edx-user_information' was not found.
            pass

        if not type_exists:
            type_object = self.base_client.types.create(type_def)

        return type_object

    def tag_customer_with_lms_user_ud(self, customer: CTCustomer, lms_user_id: int) -> CTCustomer:

        # All updates to CT Core require the version of the object you are working on as protection from out of band
        #   updates, this does mean we have to fetch every (primary) object we want to chain.

        type_object = self.ensure_custom_type_exists(TwoUCustomTypes.CUSTOMER_TYPE_DRAFT)

        # A customer can only have one custom type associated to it, and thus only one set of custom fields. THUS...
        #   They can't be required, and shouldn't entirely be relied upon; Once a proper Type is changed, the old values
        #   are LOST.

        if customer.custom and not customer.custom.type.id == type_object.id:
            raise ValueError("User already has a custom type, and its not the one were expecting, Refusing to update. "
                             "(Updating will eradicate the values from the other type, as an object may only have one "
                             "Custom Type)")

        ret = self.base_client.customers.update_by_id(customer.id, customer.version, actions=[
            CustomerSetCustomTypeAction(
                type=TypeResourceIdentifier(
                    key=TwoUCustomTypes.CUSTOMER_TYPE_DRAFT.key,
                ),
                fields=FieldContainer({EdXFieldNames.LMS_USER_ID: lms_user_id})
            ),
        ])

        return ret

        """
        Call ecommerce API overview endpoint for data about an order.

        Arguments:
            edx_lms_user_id: restrict to orders by this username
        Returns:
            dict: Dictionary represention of JSON returned from API

        See sample response in tests.py

        """
        return None
        # try:
        #     resource_url = urljoin_directory(self.api_base_url, '/orders')
        #     response = self.client.get(resource_url, params=query_params)
        #     response.raise_for_status()
        #     self.log_request_response(logger, response)
        # except RequestException as exc:
        #     self.log_request_exception(logger, exc)
        #     raise
        # return response.json()
