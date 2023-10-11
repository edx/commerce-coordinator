""" Commercetools API Client(s) Testing """
import unittest
from typing import Optional

import ddt
import pytest
from commercetools.platform.models import Type
from commercetools.testing import BackendRepository
from django.test import TestCase
import time
import uuid

import pytest
from requests_mock.adapter import Adapter

from commercetools import CommercetoolsError
from commercetools.client import Client
from commercetools.platform import models

from commerce_coordinator.apps.commercetools.catalog_info.foundational_types import TwoUCustomTypes
from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient
from commerce_coordinator.apps.core.clients import urljoin_directory
from conftest import commercetools_client_tuple
from commercetools.contrib.pytest import ct_platform_client, commercetools_api


# def test_xxxx(commercetools_client_tuple):
#     (mocker, backing_store, api_client) = commercetools_client_tuple
#     draft = TwoUCustomTypes.CUSTOMER_TYPE_DRAFT
#     ret_val = api_client.ensure_custom_type_exists(draft)
#     assert isinstance(ret_val, Type)
#     assert ret_val.key == draft.key


class ClientTests(TestCase):
    backing_store: Optional[BackendRepository] = None
    api_client: Optional[CommercetoolsAPIClient] = None

    def setUp(self) -> None:
        super().setUp()
        print("GRM: xxxxx")
        (mocker, backing_store, api_client) = commercetools_client_tuple()
        self.backing_store = backing_store
        self.api_client = api_client
        self.mocker = mocker
        breakpoint()

    def tearDown(self) -> None:
        self.backing_store = None
        self.mocker = None
        self.api_client = None
        super().tearDown()

    def test_ensure_custom_type_exists(self):
        draft = TwoUCustomTypes.CUSTOMER_TYPE_DRAFT
        ret_val = self.api_client.ensure_custom_type_exists(draft)
        assert isinstance(ret_val, Type)
        assert ret_val.key == draft.key
