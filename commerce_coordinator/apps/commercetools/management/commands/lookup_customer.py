import json

from django.core.management.base import no_translations

from commerce_coordinator.apps.commercetools.management.commands._ct_api_client_command import (
    CommercetoolsAPIClientCommand
)


class Command(CommercetoolsAPIClientCommand):
    help = "Print the current Commercetools Customer Object to the Console."

    # Django Overrides
    def add_arguments(self, parser):
        parser.add_argument("customer_uuid", nargs='?', type=str)

    @no_translations
    def handle(self, *args, **options):
        customer_uuid = options['customer_uuid']

        ret = self.ct_api_client.base_client.customers.get_by_id(customer_uuid)

        print(json.dumps(ret.serialize()))
