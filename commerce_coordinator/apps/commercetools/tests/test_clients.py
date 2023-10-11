""" Commercetools API Client(s) Testing """

from commercetools.platform.models import Type, TypeDraft
from django.test import TestCase

from commerce_coordinator.apps.commercetools.catalog_info.foundational_types import TwoUCustomTypes
from conftest import APITestingSet


class ClientTests(TestCase):
    client_set: APITestingSet

    def setUp(self) -> None:
        super().setUp()
        self.client_set = APITestingSet.new_instance()

    def test_ensure_custom_type_exists(self):
        draft = TwoUCustomTypes.CUSTOMER_TYPE_DRAFT

        assert isinstance(draft, TypeDraft)

        ret_val = self.client_set.client.ensure_custom_type_exists(draft)

        assert isinstance(ret_val, Type)
        assert ret_val.key == draft.key
