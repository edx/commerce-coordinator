import json

from django.core.management.base import no_translations

from commerce_coordinator.apps.commercetools.management.commands._ct_api_client_command import (
    CommercetoolsAPIClientCommand
)


class Command(CommercetoolsAPIClientCommand):
    help = "Tag a Customer in CT Core with an edX LMS User ID and Name"

    # Django Overrides
    def add_arguments(self, parser):
        parser.add_argument("customer_uuid", nargs='?', type=str)
        parser.add_argument("edx_lms_user_id", nargs='?', type=int)
        parser.add_argument("edx_lms_user_name", nargs='?', type=str)

    @no_translations
    def handle(self, *args, **options):
        customer_uuid = options['customer_uuid']
        edx_lms_user_id = options['edx_lms_user_id']
        edx_lms_user_name = options['edx_lms_user_name']

        customer = self.ct_api_client.base_client.customers.get_by_id(customer_uuid)

        try:
            result_customer = self.ct_api_client.tag_customer_with_lms_user_info(
                customer,
                edx_lms_user_id,
                edx_lms_user_name
            )
            print(json.dumps(result_customer.serialize()))
        except ValueError as error:
            print(error)
            exit(1)
