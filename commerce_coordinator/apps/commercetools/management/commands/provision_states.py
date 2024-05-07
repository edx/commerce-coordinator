import json

import requests
from commercetools import CommercetoolsError
from commercetools.platform.models import (
    StateChangeInitialAction,
    StateSetDescriptionAction,
    StateSetNameAction,
    StateSetTransitionsAction
)
from django.core.management.base import no_translations

from commerce_coordinator.apps.commercetools.catalog_info.foundational_types import TwoUCustomStates
from commerce_coordinator.apps.commercetools.catalog_info.utils import ls_eq
from commerce_coordinator.apps.commercetools.management.commands._ct_api_client_command import (
    CommercetoolsAPIClientCommand
)


class Command(CommercetoolsAPIClientCommand):
    help = "Add Workflow and LineItem States"

    @no_translations
    def handle(self, *args, **options):

        order_states = [
            # Order Workflow States
            TwoUCustomStates.SANCTIONED_ORDER_STATE,
            # Line Item States
            TwoUCustomStates.INITIAL_FULFILLMENT_STATE,
            TwoUCustomStates.PENDING_FULFILLMENT_STATE,
            TwoUCustomStates.PROCESSING_FULFILLMENT_STATE,
            TwoUCustomStates.SUCCESS_FULFILLMENT_STATE,
            TwoUCustomStates.FAILED_FULFILLMENT_STATE
        ]

        for state_draft in order_states:
            state = None
            try:
                state = self.ct_api_client.base_client.states.get_by_key(state_draft.key)
            except CommercetoolsError as _:  # pragma: no cover
                # commercetools.exceptions.CommercetoolsError: The Resource with key '' was not found.
                pass
            except requests.exceptions.HTTPError as _:  # The test framework doesn't wrap to CommercetoolsError
                pass

            if not state:
                state = self.ct_api_client.base_client.states.create(state_draft)

            print(json.dumps(state.serialize()))

        state_translations = {}
        state_pairs = []

        for state_draft_ref in order_states:
            state = self.ct_api_client.base_client.states.get_by_key(state_draft_ref.key)
            state_translations[state.key] = state.id
            state_translations[state.id] = state.key
            state_pairs.append((state_draft_ref, state))

        # Updating states after they have been created
        for (state_draft_ref, state) in state_pairs:
            actions = []

            # Updating the line item state transitions of the fulfillment states after they have been created
            current_transitions = [transition.id for transition in state.transitions or []]
            new_transitions = [state_translations[transition.key] for transition in state_draft_ref.transitions]

            if all(transition in current_transitions for transition in new_transitions):
                print(f'The {state.key}/{state.id} state already has the expected transitions.')
            else:
                actions.append(StateSetTransitionsAction(transitions=new_transitions))

            # Update Initial
            if state.initial != state_draft_ref.initial:
                if state_draft_ref.initial is True or state_draft_ref.initial is False:
                    actions.append(StateChangeInitialAction(initial=state_draft_ref.initial))

            if not ls_eq(state.description, state_draft_ref.description):
                actions.append(StateSetDescriptionAction(description=state_draft_ref.description))

            if not ls_eq(state.name, state_draft_ref.name):
                actions.append(StateSetNameAction(name=state_draft_ref.name))

            if actions:
                print(f'Updating {state.key}/{state.id} state...')
                # if Updating 2u-fulfillment-failure-state fails with 'initial' has no changes.
                # this is a bug in the CT api, rerun and it should be good :)
                self.ct_api_client.base_client.states.update_by_id(
                    id=state.id,
                    version=state.version,
                    actions=actions,
                )
                print(json.dumps(state.serialize()))
            else:
                print(f'{state.key}/{state.id} Has no changes...')
