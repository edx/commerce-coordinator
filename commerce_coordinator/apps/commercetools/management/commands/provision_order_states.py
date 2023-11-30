import json

import requests
from commercetools import CommercetoolsError
from django.core.management.base import no_translations

from commerce_coordinator.apps.commercetools.catalog_info.constants import TwoUKeys
from commerce_coordinator.apps.commercetools.catalog_info.foundational_types import TwoUCustomStates
from commerce_coordinator.apps.commercetools.management.commands._ct_api_client_command import (
    CommercetoolsAPIClientCommand
)


class Command(CommercetoolsAPIClientCommand):
    help = "Add Workflow States"

    @no_translations
    def handle(self, *args, **options):

        state = None

        try:
            state = self.ct_api_client.base_client.states.get_by_key(TwoUKeys.SDN_SANCTIONED_ORDER_STATE)
        except CommercetoolsError as _:  # pragma: no cover
            # commercetools.exceptions.CommercetoolsError: The Resource with key 'edx-user_information' was not found.
            pass
        except requests.exceptions.HTTPError as _:  # The test framework doesn't wrap to CommercetoolsError
            pass

        if not state:
            state = self.ct_api_client.base_client.states.create(TwoUCustomStates.SANCTIONED_ORDER_STATE)

        print(json.dumps(state.serialize()))
