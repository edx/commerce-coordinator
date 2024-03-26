import json

import requests
from commercetools import CommercetoolsError, types
from django.core.management.base import no_translations

from commerce_coordinator.apps.commercetools.catalog_info.foundational_types import TwoUCustomStates
from commerce_coordinator.apps.commercetools.management.commands._ct_api_client_command import (
    CommercetoolsAPIClientCommand
)


class Command(CommercetoolsAPIClientCommand):
    help = "Add Workflow and LineItem States"

    @no_translations
    def handle(self, *args, **options):

        order_states = [
            TwoUCustomStates.SANCTIONED_ORDER_STATE,
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


        # Updating built-in 'Initial' line item state transition to 'Fulfiment Pending' state
        initial_state = self.ct_api_client.base_client.states.get_by_key('Initial')
        pending_transition = types.StateResourceIdentifier(key=TwoUCustomStates.PENDING_FULFILLMENT_STATE.key)
        try:
            updated_initial_state = self.ct_api_client.base_client.states.update_by_id(
                id=initial_state.id,
                version=initial_state.version,
                actions=[
                    types.StateSetTransitionsAction(transitions=[pending_transition])
                ]
            )
            print('Initial state updated successfully.')
            print(json.dumps(updated_initial_state.serialize()))
        except CommercetoolsError as _:
            pass


        # Updating the transitions of the fulfillment states after they have been created
        for state_draft_ref in order_states:
            state = None
            if state_draft_ref != TwoUCustomStates.SANCTIONED_ORDER_STATE and state_draft_ref != TwoUCustomStates.SUCCESS_FULFILLMENT_STATE:
                try:
                    state = self.ct_api_client.base_client.states.get_by_key(state_draft_ref.key)
                except CommercetoolsError as _:
                    # commercetools.exceptions.CommercetoolsError: The Resource with key '' was not found.
                    pass

                if state:
                    new_transitions = None
                    current_transitions = [transition.id for transition in state.transitions]

                    if state_draft_ref == TwoUCustomStates.PENDING_FULFILLMENT_STATE:
                        new_transitions = [
                            types.StateResourceIdentifier(key=TwoUCustomStates.PROCESSING_FULFILLMENT_STATE.key)
                        ]
                    elif state_draft_ref == TwoUCustomStates.PROCESSING_FULFILLMENT_STATE:
                        new_transitions = [
                            types.StateResourceIdentifier(key=TwoUCustomStates.SUCCESS_FULFILLMENT_STATE.key),
                            types.StateResourceIdentifier(key=TwoUCustomStates.FAILED_FULFILLMENT_STATE.key)
                        ]
                    elif state_draft_ref == TwoUCustomStates.FAILED_FULFILLMENT_STATE:
                        new_transitions = [
                            types.StateResourceIdentifier(key=TwoUCustomStates.PENDING_FULFILLMENT_STATE.key)
                        ]


                    if all(transition in current_transitions for transition in new_transitions):
                        print(f'The {state.name} state already has the expected transitions.')
                    else:
                        try:
                            self.ct_api_client.base_client.states.update_by_id(
                                id=state.id,
                                version=state.version,
                                actions=[
                                    types.StateSetTransitionsAction(transitions=new_transitions)
                                ],
                            )
                            print(json.dumps(state.serialize()))
                        except CommercetoolsError as _:
                            pass

