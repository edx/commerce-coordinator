import json

from commercetools import CommercetoolsError
from commercetools.platform.models import CustomerSetCustomTypeAction, \
    CustomFieldNumberType, FieldContainer, \
    FieldDefinition, ResourceTypeId, TypeDraft, TypeResourceIdentifier, TypeTextInputHint
from django.core.management.base import no_translations

from commerce_coordinator.apps.commercetools.management.commands._api_utils import ls
from commerce_coordinator.apps.commercetools.management.commands._ct_api_client_command import \
    CommercetoolsAPIClientCommand


class Command(CommercetoolsAPIClientCommand):
    help = "Tag a Customer in CT Core with an edX LMS User ID"

    # Django Overrides
    def add_arguments(self, parser):
        parser.add_argument("customer_uuid", nargs='?', type=str)
        parser.add_argument("edx_lms_user_id", nargs='?', type=int)

    @no_translations
    def handle(self, *args, **options):
        customer_uuid = options['customer_uuid']
        edx_lms_user_id = options['edx_lms_user_id']

        # A customer can only have one custom type associated to it, and thus only one set of custom fields. THUS...
        #   They cant be required, and shouldnt entirely be relied upon, Once a Customr Type is changed the old values
        #   are LOST.

        twou_type_key = '2u-user_information'
        lms_user_id_name = 'edx-lms_user_id'

        type_exists = False
        type_object = False

        try:
            type_object = self.ct_api_client.types.get_by_key(twou_type_key)
            type_exists = True
        except CommercetoolsError as _:
            # commercetools.exceptions.CommercetoolsError: The Resource with key 'edx-user_information' was not found.
            pass

        if not type_exists:
            type_object = self.ct_api_client.types.create(TypeDraft(
                key=twou_type_key,
                name=ls({'en': '2U Cross System User Information'}),
                resource_type_ids=[ResourceTypeId.CUSTOMER],
                field_definitions=[
                    FieldDefinition(
                        type=CustomFieldNumberType(),
                        name=lms_user_id_name,
                        required=False,
                        label=ls({'en': 'edX LMS User Identifier'}),
                        input_hint=TypeTextInputHint.SINGLE_LINE
                    )
                ]
            ))

        # All updates to CT Core require the version of the object you are working on as protection from out of band
        #   updates, this does mean we have to fetch every (primary) object we want to chain.
        customer = self.ct_api_client.customers.get_by_id(customer_uuid)

        if customer.custom and not customer.custom.type.id == type_object.id:
            print("User already has a custom type, and its not the one were expecting, Refusing to update. "
                  "(Updating will eradicate the values from the other type, as an object may only have one Custom "
                  "Type)")
            exit(1)

        ret = self.ct_api_client.customers.update_by_id(customer_uuid, customer.version, actions=[
            CustomerSetCustomTypeAction(
                type=TypeResourceIdentifier(
                    key=twou_type_key,
                ),
                fields=FieldContainer({lms_user_id_name: edx_lms_user_id})
            ),
        ])

        print(json.dumps(ret.serialize()))

